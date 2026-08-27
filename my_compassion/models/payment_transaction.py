import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    my2_card_update_group_id = fields.Many2one(
        "recurring.contract.group",
        string="Card Update Group",
        readonly=True,
        help="Contract group whose saved instrument this validation"
        " transaction replaces (the update-card page with nothing due).",
    )
    my2_cardholder_name = fields.Char(
        string="Cardholder Name",
        readonly=True,
        help="Full name the provider reported for the payer, as read from its"
        " confirmed-payment notification. Used to fill in a fast-checkout"
        " sponsor's placeholder name.",
    )

    @api.model_create_multi
    def create(self, values_list):
        txs = super().create(values_list)
        # partner_name is core's snapshot of partner.name at creation time.
        # Adyen feeds it to payment_utils.split_partner_name for both the
        # drop-in payment and the monthly off-session charge
        # (payment_adyen/utils.py:format_partner_name), and that helper raises
        # IndexError on "" / AttributeError on False. Core Odoo cannot be
        # patched, so the snapshot is never left blank in the first place.
        nameless = txs.filtered(lambda tx: not tx.partner_name)
        if nameless:
            nameless.partner_name = self.env["res.partner"].MY2_PLACEHOLDER_NAME
        return txs

    def _my2_cancel_stale_checkout_tx(self):
        """Cleanup for shopper checkouts that never finished.

        A draft never reached the provider, so cancelling it is safe and
        frees the invoice it blocks. Scheduled per transaction at pay-click.

        Only drafts are cancelled. The provider owns the outcome of a
        pending transaction, which _cron_sweep_stale_pending_charges closes
        once the provider's window has passed.
        """
        self = self.sudo()  # scheduled from a public checkout session
        for tx in self.filtered(lambda t: t.state == "draft"):
            tx._set_canceled(state_message=_("The checkout was abandoned."))

    # === Cardholder name capture ===
    #
    # A fast checkout takes the payment before the sponsor says who they are,
    # so their partner carries a placeholder name. Every provider reports the
    # payer's name in its own confirmed-payment notification, which arrives
    # server-to-server and therefore also covers the sponsor who closes the
    # tab the instant they finish paying - the case the browser return and the
    # details form both miss.
    #
    # The name is read here, where the payload is, and applied in
    # _post_process, where the "payment really succeeded" gate already lives:
    # the two can run in separate requests (webhook, then the
    # payment.cron_post_process_payment_tx poll).
    #
    # Anything missing is "not available, fall through to the details form",
    # never an error: a notification must never fail over a nicety, or the
    # provider redelivers it into the same failure and the payment outcome is
    # rolled back with it.

    def _process_notification_data(self, notification_data):
        res = super()._process_notification_data(notification_data)
        try:
            name = self._my2_extract_cardholder_name(notification_data)
        except Exception:
            _logger.warning(
                "Could not read the cardholder name from the %s notification"
                " of transaction %s.",
                self.provider_code,
                self.reference,
                exc_info=True,
            )
            name = ""
        if name:
            self.my2_cardholder_name = name
        return res

    def _my2_extract_cardholder_name(self, notification_data):
        """Full name of the payer as reported by the provider, or "".

        Dispatched per provider on purpose: the field differs per provider,
        PostFinance is Switzerland-only and its field is not even confirmed to
        exist, so no shared extraction path may be assumed.
        """
        self.ensure_one()
        extract = getattr(self, f"_my2_cardholder_name_{self.provider_code}", None)
        return (extract(notification_data) or "").strip() if extract else ""

    @staticmethod
    def _my2_first_string(data, paths):
        """First non-empty string found at one of paths.

        Walks nested dicts; an int step indexes a list. Every provider payload
        is untrusted third-party JSON, so a step onto something of the wrong
        shape abandons that path instead of raising.
        """
        for path in paths:
            value = data
            for key in path:
                if isinstance(key, int):
                    is_index = isinstance(value, list) and len(value) > key
                    value = value[key] if is_index else None
                elif isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                if value is None:
                    break
            if isinstance(value, str) and value.strip():
                return value
        return ""

    def _my2_cardholder_name_stripe(self, notification_data):
        """Stripe reports billing_details.name on the Charge of the
        payment_intent.succeeded notification. The PaymentMethod object of the
        browser return carries the same field, and whether the Charge comes
        expanded depends on the API version, so every shape is read."""
        return self._my2_first_string(
            notification_data,
            [
                ("charge", "billing_details", "name"),
                ("payment_method", "billing_details", "name"),
                ("payment_intent", "latest_charge", "billing_details", "name"),
                ("payment_intent", "charges", "data", 0, "billing_details", "name"),
            ],
        )

    def _my2_cardholder_name_adyen(self, notification_data):
        """Adyen reports additionalData.cardHolderName ("Include Card Holder")
        or shopperName ("Include Shopper Details"). Neither is on by default:
        both are merchant-account settings someone has to enable in the Adyen
        Customer Area, so a missing value is the expected state until then.
        paymentMethod.holderName only comes from the browser return, where the
        payment method arrives as an object rather than a code."""
        name = self._my2_first_string(
            notification_data,
            [
                ("additionalData", "cardHolderName"),
                ("paymentMethod", "holderName"),
            ],
        )
        if name:
            return name
        shopper_name = notification_data.get("shopperName")
        if isinstance(shopper_name, dict):
            parts = (
                shopper_name.get("firstName") or "",
                shopper_name.get("lastName") or "",
            )
            return " ".join(part for part in parts if part.strip())
        return ""

    def _my2_cardholder_name_postfinance(self, notification_data):
        """Switzerland only, and deliberately a no-op.

        No cardholder-name field could be found in PostFinance Checkout's docs
        or SDK (the "Cardholder" models are 3-D Secure authentication data),
        and the field is said to depend on the acceptance partner. Its
        notification payload does not carry the transaction data either - the
        handler re-fetches it through the SDK - so filling this in means
        reading the fetched object, which is exactly why this stays a separate
        method: CH can implement it here without touching anything shared.
        """
        return ""

    def _my2_apply_cardholder_name(self):
        """Fill in a fast-checkout sponsor's placeholder name.

        Split with payment_utils.split_partner_name, the same helper the
        providers use in the other direction, so a compound name is treated
        the same everywhere. The sponsor reviews and corrects it on the
        details form, so an imperfect split is not a problem; overwriting a
        real name would be, which _my2_replace_placeholder_name prevents.
        """
        for tx in self:
            if not tx.my2_cardholder_name:
                continue
            partner = tx.partner_id.sudo()
            if not partner.my2_name_placeholder:
                continue
            firstname, lastname = payment_utils.split_partner_name(
                tx.my2_cardholder_name
            )
            partner._my2_replace_placeholder_name(firstname, lastname)

    def _post_process(self):
        """Post-processing of digital-mode contract payments.

        - Keep the collection group's saved token current: a confirmed
          tokenized transaction is the instrument the monthly off-session
          charge must use from now on.
        - Run invoice_paid on the settled invoices' contracts: provider
          payments reconcile invoices into 'in_payment' (outstanding
          account), which the bank-statement reconcile hook - the usual
          invoice_paid trigger - ignores, so waiting contracts would never
          activate.
        - Give a fast-checkout sponsor the name the provider reported, so
          their placeholder is gone before anything greets them by it.
        """
        res = super()._post_process()
        done = self.filtered(lambda t: t.state == "done")
        # Before the contract handling below: activation is what sends the
        # portal invitation, and the invitation waits for a real name.
        done._my2_apply_cardholder_name()
        for tx in done:
            digital_invoices = tx.invoice_ids.filtered(
                "line_ids.contract_id.group_id.payment_mode_id.payment_provider_id"
            )
            if digital_invoices and not digital_invoices.filtered(
                lambda m: m.state == "posted"
            ):
                # money was captured but every target invoice is gone
                # (e.g. the signup was reverted while the charge was in
                # flight) - surface it, staff must refund or re-post
                _logger.error(
                    "Transaction %s is done but its invoices %s are all "
                    "cancelled: captured payment needs manual handling.",
                    tx.reference,
                    digital_invoices.mapped("name"),
                )
            if tx.token_id:
                # A group with no saved card takes the one that just paid.
                # Replacing an existing card is only allowed from the
                # update-card page, which authenticates the sponsor first.
                groups = (
                    digital_invoices.line_ids.contract_id.group_id
                    | tx.my2_card_update_group_id
                ).filtered(
                    lambda g, tx=tx: g.payment_mode_id.payment_provider_id
                    and g.payment_token_id != tx.token_id
                    and (not g.payment_token_id or g == tx.my2_card_update_group_id)
                )
                try:
                    groups.payment_token_id = tx.token_id
                except (ValidationError, UserError):
                    # A token incompatible with the group must never wedge the
                    # post-processing poll or cron into an eternal retry. The
                    # partner constraint raises one error, the company the
                    # other.
                    _logger.error(
                        "Could not save token %s on groups %s (tx %s);"
                        " monthly charges keep using the previous card.",
                        tx.token_id.id,
                        groups.ids,
                        tx.reference,
                        exc_info=True,
                    )
            for invoice in digital_invoices.filtered(
                lambda m: m.payment_state in ("paid", "in_payment")
            ):
                try:
                    invoice.line_ids.contract_id.invoice_paid(invoice)
                except UserError:
                    # e.g. a contract cancelled between charge and
                    # settlement - never break the poll/cron post-processing
                    _logger.error(
                        "invoice_paid failed for invoice %s (tx %s); "
                        "activation/handling left to staff.",
                        invoice.name,
                        tx.reference,
                        exc_info=True,
                    )
        return res
