from werkzeug.exceptions import NotFound

from odoo import Command, _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal

from ..models.contract_group import UPDATE_CARD_TOKEN_SCOPE
from .website_utils import ensure_recurring_instrument


class MyCompassionUpdateCard(payment_portal.PaymentPortal):
    """Card-replacement page for digital-mode contract groups.

    With arrears: the group's due invoices are settled with the new card in
    one tokenizing payment. Without: a validation transaction verifies the
    card. Either way the saved instrument swaps through transaction
    post-processing and every later monthly charge uses the new card.
    """

    # shared with recurring.contract.group._my2_update_card_url, which
    # signs the links the dunning emails embed
    ACCESS_TOKEN_SCOPE = UPDATE_CARD_TOKEN_SCOPE
    # by then any 3DS challenge is long expired: an unfinished checkout
    # transaction is cancelled so it stops blocking the group's invoices
    CHECKOUT_CLEANUP_MINUTES = 60

    @staticmethod
    def _fetch_guarded_group(group_id, access_token):
        """Return the sudoed group, or 404 on a bad id or failed auth.

        Auth: the signed link of the dunning/pre-expiry emails
        (generate_access_token(ACCESS_TOKEN_SCOPE, group.id, partner.id)),
        or a logged-in user whose commercial partner owns the group.
        """
        try:
            group_id = int(group_id)
        except (TypeError, ValueError) as error:
            raise NotFound() from error
        group = request.env["recurring.contract.group"].sudo().browse(group_id)
        if not group.exists():
            raise NotFound()
        user = request.env.user
        is_owner = (
            not user._is_public()
            and user.partner_id.commercial_partner_id
            == group.partner_id.commercial_partner_id
        )
        if not is_owner and not payment_utils.check_access_token(
            access_token,
            MyCompassionUpdateCard.ACCESS_TOKEN_SCOPE,
            group.id,
            group.partner_id.id,
        ):
            raise NotFound()  # don't leak record ids
        return group

    @http.route(
        "/my2/update-card",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def update_card_page(self, group_id=None, access_token=None, **kwargs):
        group = self._fetch_guarded_group(group_id, access_token)
        provider = group.payment_mode_id.payment_provider_id
        if not provider:
            raise NotFound()  # nothing card-like to update on a bank group
        invoices = group._due_digital_invoices()
        return request.render(
            "my_compassion.my2_update_card_page",
            self._get_update_card_values(group, provider, access_token, invoices),
        )

    @http.route(
        "/my2/update-card/transaction/<int:group_id>",
        type="json",
        auth="public",
        website=True,
    )
    def update_card_transaction(self, group_id, access_token=None, **kwargs):
        """Create the card-replacement transaction and return its
        processing values: a tokenizing payment of the due invoices, or a
        validation transaction when nothing is due."""
        group = self._fetch_guarded_group(group_id, access_token)
        provider = group.payment_mode_id.payment_provider_id
        if not provider:
            raise ValidationError(
                _("This account has no online payment method to update.")
            )
        self._validate_transaction_kwargs(
            kwargs,
            additional_allowed_keys=(
                "reference_prefix",
                "currency_id",
                "partner_id",
            ),
        )
        if kwargs.get("flow") == "token":
            # the page exists to capture a NEW instrument
            raise ValidationError(_("Please enter a new payment method."))
        landing_route = self._update_card_landing_route(group, access_token)
        # the due set is recomputed at pay-click: a charge that settled the
        # arrears since the render (e.g. the nightly cron) degrades this
        # to a validation
        overrides, custom_create_values = self._update_card_tx_values(
            group, group._due_digital_invoices()
        )
        # Server-side truth: the client never chooses what is charged, by
        # whom, through which provider, nor where it lands.
        kwargs.update(
            partner_id=group.partner_id.id,
            provider_id=provider.id,
            landing_route=landing_route,
            **overrides,
        )
        tx_sudo = self._create_transaction(
            custom_create_values=custom_create_values,
            my2_sponsorship=True,
            **kwargs,
        )
        self._finalize_update_card_tx(tx_sudo, landing_route)
        return tx_sudo._get_processing_values()

    @staticmethod
    def _update_card_landing_route(group, access_token):
        route = f"/my2/update-card/done?group_id={group.id}"
        if access_token:
            route += f"&access_token={access_token}"
        return route

    @staticmethod
    def _update_card_tx_values(group, invoices):
        """Transaction parameters of the card replacement: a payment of
        the due invoices, or a card validation when nothing is due.
        Returns (kwargs overrides, custom create values)."""
        if invoices:
            invoices._my2_serialize_charge_attempts()
            return (
                {
                    "currency_id": invoices[0].currency_id.id,
                    "amount": sum(invoices.mapped("amount_residual")),
                    "is_validation": False,
                },
                {"invoice_ids": [Command.set(invoices.ids)]},
            )
        return (
            {"amount": None, "currency_id": None, "is_validation": True},
            {"my2_card_update_group_id": group.id},
        )

    def _finalize_update_card_tx(self, tx_sudo, landing_route):
        """The created transaction must actually replace the card, report
        its own outcome on the landing page, and never linger unfinished."""
        ensure_recurring_instrument(tx_sudo)
        tx_sudo.landing_route = f"{landing_route}&tx_id={tx_sudo.id}"
        # unfinished checkouts would block the group's invoices forever
        tx_sudo.with_delay_sh(
            "_my2_cancel_stale_checkout_tx",
            eta=self.CHECKOUT_CLEANUP_MINUTES * 60,
            identity_key=f"card_update_cleanup.{tx_sudo.id}",
        )

    @http.route(
        "/my2/update-card/done",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def update_card_done(self, group_id=None, access_token=None, tx_id=None, **kwargs):
        """Outcome page: the payment status flow lands here on ANY final
        transaction state. A refused card must not be reported as
        updated to the very audience whose cards are failing."""
        group = self._fetch_guarded_group(group_id, access_token)
        try:
            tx = request.env["payment.transaction"].sudo().browse(int(tx_id)).exists()
        except (TypeError, ValueError):
            tx = request.env["payment.transaction"].sudo()
        belongs_to_group = tx and (
            tx.my2_card_update_group_id == group
            or (
                tx.invoice_ids and tx.invoice_ids.line_ids.contract_id.group_id == group
            )
        )
        retry_url = f"/my2/update-card?group_id={group.id}"
        if access_token:
            retry_url += f"&access_token={access_token}"
        return request.render(
            "my_compassion.my2_update_card_done_page",
            {
                "group": group,
                "success": bool(belongs_to_group and tx.state == "done"),
                "retry_url": retry_url,
            },
        )

    @classmethod
    def _get_update_card_values(cls, group, provider, access_token, invoices):
        """Rendering context for payment.form, scoped to the group's
        provider with forced tokenization (same keys the generic
        /payment/pay page builds)."""
        partner = group.partner_id
        currency = invoices[0].currency_id if invoices else group.company_id.currency_id
        # The context flag reaches the provider inline form rendering
        # through these recordsets. It tells _is_tokenization_required
        # that this page must save the card (see that method).
        providers_sudo = provider.sudo().with_context(my2_sponsorship=True)
        payment_methods_sudo = (
            request.env["payment.method"]
            .sudo()
            .with_context(my2_sponsorship=True)
            ._get_compatible_payment_methods(
                providers_sudo.ids,
                partner.id,
                currency_id=currency.id,
                force_tokenization=True,
            )
        )
        amount = sum(invoices.mapped("amount_residual"))
        return {
            "group": group,
            "current_card": group.payment_token_id,
            "mode": "payment" if amount else "validation",
            "reference_prefix": None,
            "amount": amount,
            "currency": currency,
            "partner_id": partner.id,
            "providers_sudo": providers_sudo,
            "payment_methods_sudo": payment_methods_sudo,
            # never offer stored instruments: a new card is the point
            "tokens_sudo": request.env["payment.token"].sudo(),
            "availability_report": {},
            "transaction_route": f"/my2/update-card/transaction/{group.id}",
            "landing_route": f"/my2/update-card/done?group_id={group.id}",
            "access_token": access_token,
            "show_tokenize_input_mapping": (
                payment_portal.PaymentPortal._compute_show_tokenize_input_mapping(
                    providers_sudo, my2_sponsorship=True
                )
            ),
        }
