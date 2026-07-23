##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import random
import uuid
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import BadRequest, NotFound

from odoo import Command, fields, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal

from ..models.compassion_child import ChildNotFound

# Hold up to 3 children (more is too slow)
GLOBAL_FETCH_LIMIT = 3


def _product_display_price(default_code):
    """Monthly amount of a contract product, as rendered in the wizard copy.
    Same product lookup as the contract lines (default_code), scoped to the
    website's company: a company-specific product wins over a shared one.
    """
    company = request.website.company_id
    products = (
        request.env["product.template"]
        .sudo()
        .with_company(company)
        .search(
            [
                ("default_code", "=", default_code),
                ("company_id", "in", [company.id, False]),
            ]
        )
    )
    product = products.filtered(lambda p: p.company_id == company)[:1] or products[:1]
    return f"{product.list_price:g}" if product else ""


def _get_reservation_uuid():
    reservation_uuid = request.session.get("reservation_uuid")
    if not reservation_uuid:
        if request.env.user._is_public():
            reservation_uuid = str(uuid.uuid4())
        else:
            reservation_uuid = request.env.user.partner_id.uuid
        request.session["reservation_uuid"] = reservation_uuid
    return reservation_uuid


class MyCompassionSponsorshipsController(http.Controller):
    @http.route(
        "/my2/sponsorships", type="http", auth="public", website=True, sitemap=False
    )
    def my2_render_sponsorships_page(self, **kwargs):
        """
        Renders the sponsorships landing page.
        return: An HTTP response containing a rendered template with the
        sponsorships landing page.
        """
        countries = request.env["compassion.field.office"].search(
            [
                ("available_on_childpool", "=", True),
                ("field_office_id", "!=", "ID"),  # Indonesia has two field offices
            ]
        )

        return request.render(
            "my_compassion.my2_sponsorships_page",
            {
                "countries": countries,
                "sponsorship_type": "standard",
            },
        )

    @http.route(
        "/my2/write-and-pray", type="http", auth="public", website=True, sitemap=False
    )
    def my2_render_write_and_pray_page(self, **kwargs):
        """
        Renders the write and pray variant of the sponsorships page.
        return: An HTTP response containing a rendered template with the
        sponsorships landing page.
        """
        countries = request.env["compassion.field.office"].search(
            [("available_on_childpool", "=", True)]
        )

        return request.render(
            "my_compassion.my2_sponsorships_page",
            {
                "countries": countries,
                "sponsorship_type": "write_and_pray",
            },
        )

    @http.route(
        "/my2/sponsorships/fetch",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def fetch_sponsorships(
        self, limit: int = 20, offset: int = 0, global_pool: bool = False, **post
    ):
        """
        Fetches children available for sponsorship and renders them using the
        my_compassion.my2_sponsorships_results_content template.
        return: An JSON response containing the rendered template html
        as well as the new children count and total hits.
        """
        child_obj = request.env["compassion.child"].sudo()
        if global_pool:
            try:
                post["limit"] = GLOBAL_FETCH_LIMIT
                child_obj.website_hold_child(post)
            except ChildNotFound:
                # Error is already logged, the frontend will just show no results
                pass
        # Query matching children
        domain = self._get_filtered_domain(post)
        total_results = child_obj.search_count(domain)
        children = child_obj.search(
            domain,
            limit=limit,
            offset=offset,
            order="unsponsored_since asc, create_date asc, completion_date asc",
        )

        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_sponsorships_results_content",
            {
                "children": children,
                "sponsorship_type": post.get("sponsorship_type", "standard"),
            },
        )

        return {
            "html": html_content,
            "count": len(children),
            "total": total_results,
        }

    @http.route(
        "/my2/sponsorships/fetch-random",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def fetch_random_child(self, **post):
        """
        Fetches a random child matching the search criteria.
        return: An JSON response containing the id of the random child.
        """
        # Get domain from filters
        domain = self._get_filtered_domain(post)

        # Query matching children
        child_obj = request.env["compassion.child"]
        total_results = child_obj.search_count(domain)

        child = None
        html_content = ""
        if total_results != 0:
            children = child_obj.search(
                domain,
                limit=1,
                offset=random.randint(0, total_results - 1),
            )

            if children:
                child = children[0]

                html_content = request.env["ir.qweb"]._render(
                    "my_compassion.my2_sponsorships_results_content",
                    {
                        "children": children,
                        "sponsorship_type": post.get("sponsorship_type", "standard"),
                    },
                )

        return {
            "child_id": child.id if child else None,
            "html": html_content,
        }

    @classmethod
    def _get_filtered_domain(cls, post):
        gender = post.get("gender", "either")
        age_min = int(post.get("age_min", 0))
        age_max = int(post.get("age_max", 18))
        country = post.get("country", "")

        child_obj = request.env["compassion.child"]

        # Filter by availability
        domain = [
            ("is_published", "=", True),
            ("state", "in", child_obj._available_states()),
            ("hold_id.expiration_date", ">", fields.Datetime.now()),
            ("hold_id.state", "=", "active"),
            "|",
            ("website_reservation_date", "=", False),
            "&",
            ("website_reservation_id", "=", request.session.session_token),
            ("website_reservation_id", "!=", False),
        ]

        # Filter by age
        domain += [
            ("age", ">=", age_min),
            ("age", "<=", age_max),
        ]

        # Filter by gender
        if gender != "either":
            domain += [("gender", "=", gender)]

        # Filter by country
        if country != "":
            domain += [("field_office_id.field_office_id", "=", country)]

        return domain


class MyCompassionNewSponsorshipController(http.Controller):
    @http.route(
        '/my2/new-sponsorship/<model_safe("compassion.child"):child>',
        type="http",
        auth="public",
        website=True,
    )
    def wizard_start(self, child, sponsorship_type="standard", **kwargs):
        """
        Renders the new sponsorship wizard initial page.

        UTM tracking from query params is handled by Odoo's utm.mixin model.

        return: An HTTP response containing a rendered template
        with the initial wizard page.
        """
        child = child.sudo()
        if not child.exists() or child.state not in child._available_states():
            raise NotFound()

        # Reserve child for 5 minutes
        reservation_uuid = _get_reservation_uuid()
        if not child.reserve_for_web_sponsorship(reservation_uuid):
            return request.render(
                "my_compassion.child_unavailable_page",
                {
                    "child": child,
                    "sponsorship_type": sponsorship_type,
                },
            )

        # Create new wizard
        wizard = request.env["new.sponsorship.wizard"].create(
            {
                "child_id": child.id,
                "user_id": request.env.user.id,
                "sponsorship_type": sponsorship_type,
                "company_id": request.website.company_id.id,
                "birthdate": request.env.user.birthdate_date
                if not request.env.user._is_public()
                else False,
            }
        )

        return request.render(
            "my_compassion.my2_new_sponsorship_wizard_page",
            {
                "form_content_html": self._render_form_content(wizard),
                "additional_title": _("Payment options"),
            },
        )

    @http.route(
        "/my2/new-sponsorship/step",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def wizard_step(self, **post):
        """
        Takes a step (forward or backward) in the new sponsorship wizard
        and renders the new wizard content using the
        my_compassion.my2_new_sponsorship_wizard_form_content template.
        return: An JSON response containing the rendered template html.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Update the record
        wizard.update(post)

        if wizard.is_done:
            return {"finish": True}
        else:
            return {"html": self._render_form_content(wizard)}

    @http.route(
        "/my2/new-sponsorship/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def sponsorship_wizard_submit(self, **post):
        """
        Receives the wizard form submission and finalizes the new sponsorship,
        then redirect to the thank-you page.
        return: A redirection to the thank-you page.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Cancel if person is too old for Write&Pray
        if (
            wizard.sponsorship_type == "write_and_pray"
            and wizard.birthdate
            < (fields.Datetime.now() - relativedelta(years=25)).date()
        ):
            raise BadRequest()

        # Make sure child is still available and finalize sponsorship creation
        if wizard.child_id.state not in wizard.child_id._available_states():
            return request.render(
                "my_compassion.child_unavailable_page",
                {
                    "child": wizard.child_id,
                    "sponsorship_type": wizard.sponsorship_type,
                },
            )
        sponsorship = wizard.finish_sponsorship()

        # Digital modes pay the first month live before the thank-you.
        if sponsorship.payment_mode_id.payment_provider_id:
            access_token = payment_utils.generate_access_token(
                sponsorship.id, sponsorship.partner_id.id
            )
            return request.redirect(
                f"/my2/new-sponsorship/payment?sponsorship_id={sponsorship.id}"
                f"&access_token={access_token}"
            )

        # Redirect to thank-you page
        return request.redirect(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )

    @http.route(
        "/my2/new-sponsorship/thank-you", type="http", auth="public", website=True
    )
    def wizard_thank_you(self, sponsorship_id=None, **kwargs):
        """
        Renders the new sponsorship thank-you page.
        return: An HTTP response containing a rendered template with the thank-you page.
        """
        try:
            sponsorship_id = int(sponsorship_id)
        except (TypeError, ValueError) as error:
            raise NotFound() from error
        sponsorship = request.env["recurring.contract"].sudo().browse(sponsorship_id)

        return request.render(
            "my_compassion.my2_new_sponsorship_thank_you_page",
            {
                "n_steps": 3,
                "sponsorship": sponsorship,
                "additional_title": _("Thank you"),
            },
        )

    @staticmethod
    def _render_form_content(wizard):
        # Fetch available salutations, countries, payment methods,
        # languages and lead sources
        titles = (
            request.env["res.partner.title"]
            .sudo()
            .search([("is_shown_on_public_forms", "=", True)])
        )
        countries = request.env["res.country"].search([])
        spoken_languages = (
            request.env["res.lang.compassion"]
            .sudo()
            .search([("translatable", "=", True)])
        )
        payment_methods = (
            request.env["account.payment.mode"]
            .sudo()
            .search(
                [
                    ("website_published", "=", True),
                    ("company_id", "=", request.website.company_id.id),
                ]
            )
        )
        lead_sources = (
            request.env["recurring.contract.origin"]
            .sudo()
            .search(
                [
                    ("website_published", "=", True),
                ]
            )
        )
        currency_name = request.website.company_id.currency_id.name

        # Send the user back to the exact URL they came from after login,
        # preserving every query param (UTM, sponsorship_type, anything else).
        login_url_redirect = (
            f"/web/login?{urlencode({'redirect': request.httprequest.full_path})}"
        )

        # Render step template first
        inner_step_html = request.env["ir.qweb"]._render(
            wizard.current_step.template.id,
            {
                "wizard": wizard,
                "titles": titles,
                "countries": countries,
                "payment_methods": payment_methods,
                "spoken_languages": spoken_languages,
                "lead_sources": lead_sources,
                "currency_name": currency_name,
                "sponsorship_amount": _product_display_price("sponsorship"),
                "sponsorship_plus_extra": _product_display_price("fund_gen"),
                "login_url_redirect": login_url_redirect,
            },
        )

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_new_sponsorship_wizard_form_content",
            {
                "wizard": wizard,
                "inner_step_html": inner_step_html,
                "currency_name": currency_name,
            },
        )

        return html_content


class MyCompassionSponsorshipPayment(payment_portal.PaymentPortal):
    """First-payment checkout for sponsorships collected by an online
    payment provider. Extends PaymentPortal for the _create_transaction /
    _validate_transaction_kwargs helpers."""

    @http.route(
        "/my2/new-sponsorship/payment",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def sponsorship_payment_page(self, sponsorship_id=None, access_token=None, **kwargs):
        sponsorship = self._fetch_guarded_sponsorship(sponsorship_id, access_token)
        provider = sponsorship.payment_mode_id.payment_provider_id
        if not provider or sponsorship.state not in ("draft", "waiting"):
            if sponsorship.state in ("cancelled", "terminated"):
                # reverted/closed signup: this checkout no longer exists
                return request.redirect("/my2/children")
            # already paid / not a digital contract -> normal thank-you
            return request.redirect(
                f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
            )
        # Generate the first invoice NOW so the displayed amount is the very
        # amount the transaction route will charge (a group with another due
        # contract yields a merged invoice above the monthly amount), and arm
        # the cleanup for sponsors who leave without clicking pay.
        invoice = sponsorship._ensure_first_invoice()
        if not invoice:
            # nothing chargeable (generation suspended/blocked): leave the
            # waiting contract to staff instead of showing a broken checkout
            return request.redirect(
                f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
            )
        sponsorship._schedule_digital_revert()
        rendering_values = self._get_sponsorship_payment_values(
            sponsorship, provider, access_token, invoice
        )
        return request.render(
            "my_compassion.my2_new_sponsorship_payment_page", rendering_values
        )

    @staticmethod
    def _is_sponsorship_user(sponsorship):
        """Whether the current session is authenticated as the sponsor."""
        user = request.env.user
        return (
            not user._is_public()
            and user.partner_id.commercial_partner_id
            == sponsorship.partner_id.commercial_partner_id
        )

    @staticmethod
    def _fetch_guarded_sponsorship(sponsorship_id, access_token):
        """Return the sudoed sponsorship or raise 404 on a bad id/token."""
        try:
            sponsorship_id = int(sponsorship_id)
        except (TypeError, ValueError) as error:
            raise NotFound() from error
        sponsorship = (
            request.env["recurring.contract"].sudo().browse(sponsorship_id)
        )
        if not sponsorship.exists() or not payment_utils.check_access_token(
            access_token, sponsorship.id, sponsorship.partner_id.id
        ):
            raise NotFound()  # don't leak record ids
        return sponsorship

    @http.route(
        "/my2/new-sponsorship/transaction/<int:sponsorship_id>",
        type="json",
        auth="public",
        website=True,
    )
    def sponsorship_payment_transaction(self, sponsorship_id, access_token=None, **kwargs):
        """Create the tokenizing first-payment transaction of a sponsorship,
        linked to its first invoice, and return its processing values."""
        sponsorship = self._fetch_guarded_sponsorship(sponsorship_id, access_token)
        provider = sponsorship.payment_mode_id.payment_provider_id
        if not provider or sponsorship.state not in ("draft", "waiting"):
            raise ValidationError(
                _("This sponsorship can no longer be paid online.")
            )
        self._validate_transaction_kwargs(
            kwargs,
            additional_allowed_keys=(
                "reference_prefix",
                "currency_id",
                "partner_id",
            ),
        )
        if kwargs.get("flow") == "token" and not self._is_sponsorship_user(
            sponsorship
        ):
            # saved instruments are only offered/chargeable to the logged-in
            # sponsor: the public wizard matches partners by email, which
            # must never give access to someone else's stored card
            raise ValidationError(
                _("Please log in to pay with a saved payment method.")
            )
        invoice = sponsorship._ensure_first_invoice()
        # schedule the cleanup no matter how the checkout continues
        sponsorship._schedule_digital_revert()
        if not invoice:
            raise ValidationError(
                _("There is nothing to pay for this sponsorship.")
            )
        # Server-side truth: the client never chooses what is charged, by
        # whom, through which provider, nor where it lands.
        kwargs.update(
            partner_id=sponsorship.partner_id.id,
            currency_id=invoice.currency_id.id,
            amount=invoice.amount_residual,
            provider_id=provider.id,
            is_validation=False,
            landing_route=(
                f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
            ),
        )
        tx_sudo = self._create_transaction(
            custom_create_values={"invoice_ids": [Command.set(invoice.ids)]},
            my2_sponsorship=True,
            **kwargs,
        )
        return tx_sudo._get_processing_values()

    @classmethod
    def _get_sponsorship_payment_values(
        cls, sponsorship, provider, access_token, invoice
    ):
        """Rendering context for payment.form, scoped to the sponsorship's
        provider (same keys the generic /payment/pay page builds). The
        amount is the first invoice's residual - exactly what the
        transaction route charges."""
        partner = sponsorship.partner_id
        currency = invoice.currency_id
        providers_sudo = provider.sudo()
        payment_methods_sudo = (
            request.env["payment.method"]
            .sudo()
            ._get_compatible_payment_methods(
                providers_sudo.ids,
                partner.id,
                currency_id=currency.id,
                force_tokenization=True,
                my2_sponsorship=True,
            )
        )
        # saved instruments only for the authenticated sponsor: the public
        # wizard matches partners by email, which must never expose someone
        # else's stored cards
        tokens_sudo = request.env["payment.token"].sudo()
        if cls._is_sponsorship_user(sponsorship):
            tokens_sudo = tokens_sudo._get_available_tokens(
                providers_sudo.ids, partner.id
            )
        return {
            "sponsorship": sponsorship,
            "reference_prefix": sponsorship.reference,
            "amount": invoice.amount_residual,
            "monthly_amount": sponsorship.total_amount,
            "currency": currency,
            "partner_id": partner.id,
            "providers_sudo": providers_sudo,
            "payment_methods_sudo": payment_methods_sudo,
            "tokens_sudo": tokens_sudo,
            "availability_report": {},
            "transaction_route": (
                f"/my2/new-sponsorship/transaction/{sponsorship.id}"
            ),
            "landing_route": (
                f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
            ),
            "access_token": access_token,
            "show_tokenize_input_mapping": (
                payment_portal.PaymentPortal._compute_show_tokenize_input_mapping(
                    providers_sudo, my2_sponsorship=True
                )
            ),
        }
