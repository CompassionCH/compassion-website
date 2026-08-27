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
from .website_utils import ensure_recurring_instrument, safe_int

# Hold up to 3 children (more is too slow)
GLOBAL_FETCH_LIMIT = 3

# Signups this browser session created. It is the proof, on the thank-you
# page, that the visitor is the one who just went through the checkout -
# a bare sponsorship_id in the URL proves nothing, and the details token must
# never be handed out on one. Only the most recent ones are kept: the session
# is a cookie-sized store, and nobody returns to an old thank-you page.
OWN_SIGNUPS_SESSION_KEY = "my2_own_sponsorship_ids"
OWN_SIGNUPS_SESSION_LIMIT = 10


def _flow_n_steps(sponsorship):
    """Step count of the wizard flow that created this sponsorship.

    The payment and thank-you pages continue the wizard's progress bar, so
    they have to count the same steps. The wizard record itself is long gone
    by then, but its flow is fully determined by the sponsorship type and
    whether the visitor is logged in.
    """
    return (
        request.env["new.sponsorship.wizard"]
        .sudo()
        ._flow_n_steps(
            "write_and_pray" if sponsorship.type == "SWP" else "standard",
            request.env.user._is_public(),
        )
    )


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

        Write&Pray is Switzerland-only: the free, no-financial-support
        godparent role it offers is not a product the other countries sell.

        return: An HTTP response containing a rendered template with the
        sponsorships landing page.
        """
        if request.website.company_id.country_id.code != "CH":
            raise NotFound()

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
        limit = max(1, safe_int(limit, 20))
        offset = max(0, safe_int(offset, 0))
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
        age_min = safe_int(post.get("age_min"), 0)
        age_max = safe_int(post.get("age_max"), 18)
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
        # Write&Pray is Switzerland-only; see my2_render_write_and_pray_page.
        if (
            sponsorship_type == "write_and_pray"
            and request.website.company_id.country_id.code != "CH"
        ):
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
        wizard_id = safe_int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id).exists()
        if not wizard:
            raise BadRequest()

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
        wizard_id = safe_int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id).exists()
        if not wizard:
            raise BadRequest()

        # Cancel if person is too old for Write&Pray. The birthdate is asked
        # by the Write&Pray step itself, so a submission without one is a
        # tampered form, not an age to compare (False < date raises).
        if wizard.sponsorship_type == "write_and_pray" and (
            not wizard.birthdate
            or wizard.birthdate
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
        own_signups = list(request.session.get(OWN_SIGNUPS_SESSION_KEY) or [])
        own_signups.append(sponsorship.id)
        request.session[OWN_SIGNUPS_SESSION_KEY] = own_signups[
            -OWN_SIGNUPS_SESSION_LIMIT:
        ]

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
    def wizard_thank_you(
        self, sponsorship_id=None, details_token=None, details_emailed=None, **kwargs
    ):
        """
        Renders the new sponsorship thank-you page. Sponsors whose details are
        still missing get the "Who shall we thank?" form on it.

        details_token is the credential of the emailed "finish later" link.
        details_emailed marks the render right after such a mail was sent, so
        the page says so instead of offering the form again.
        return: An HTTP response containing a rendered template with the thank-you page.
        """
        sponsorship = self._fetch_signup(sponsorship_id)
        if not sponsorship._my2_check_details_token(
            details_token
        ) and not self._owns_signup(sponsorship):
            # The thank-you page is public, but the sponsorship details
            # are private. If this visitor is not the sponsor, hide them.
            raise NotFound()
        return request.render(
            "my_compassion.my2_new_sponsorship_thank_you_page",
            self._thank_you_values(
                sponsorship,
                details_token=details_token,
                details_emailed=details_emailed,
            ),
        )

    @http.route(
        "/my2/new-sponsorship/complete-details",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def sponsorship_complete_details(
        self, sponsorship_id=None, details_token=None, **post
    ):
        """
        Receives the "Who shall we thank?" form: the sponsor's name and phone,
        plus their address if they chose to give one.

        The token is the whole gate (see _fetch_details_signup) - nothing
        posted here is trusted, the required fields included.
        return: A redirection to the thank-you page, which now has no form
        left to show, or the form again with an error when a required field
        came back empty.
        """
        sponsorship = self._fetch_details_signup(sponsorship_id, details_token)
        values = self._details_form_values(post)
        if not (values["firstname"] and values["lastname"] and values["phone"]):
            return request.render(
                "my_compassion.my2_new_sponsorship_thank_you_page",
                self._thank_you_values(
                    sponsorship,
                    details_token=details_token,
                    details_error=_("Please tell us your name and phone number."),
                    submitted=values,
                ),
            )
        sponsorship._my2_apply_details(values)
        return request.redirect(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )

    @http.route(
        "/my2/new-sponsorship/details-later",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def sponsorship_details_later(
        self, sponsorship_id=None, details_token=None, **post
    ):
        """
        The "Do this later - we will email you" escape hatch of the details
        form: mails the sponsor a link back to it and drops the form from the
        page.

        Gated by the same token as the form itself, so this cannot be turned
        into "post a sponsorship id, mail that sponsor".
        return: A redirection to the thank-you page, telling them to look in
        their mailbox.
        """
        sponsorship = self._fetch_details_signup(sponsorship_id, details_token)
        sponsorship._my2_send_details_reminder()
        return request.redirect(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
            "&details_emailed=1"
        )

    @staticmethod
    def _fetch_signup(sponsorship_id):
        """The sudoed signup of a public page, or 404 on a bad id."""
        try:
            sponsorship_id = int(sponsorship_id)
        except (TypeError, ValueError) as error:
            raise NotFound() from error
        sponsorship = (
            request.env["recurring.contract"].sudo().browse(sponsorship_id).exists()
        )
        if not sponsorship:
            raise NotFound()
        return sponsorship

    @classmethod
    def _fetch_details_signup(cls, sponsorship_id, details_token):
        """The signup a details submission may write to, or 404.

        The token is the only gate, and it is checked against the very
        contract the request names: a token minted for one signup must not
        open another. 404 rather than 403 everywhere, so a wrong, expired,
        already-used or foreign token tells nothing apart from a wrong id.

        Locked (see _my2_serialize_details_submission) before the check, so
        two overlapping submissions of the same token cannot both pass it:
        the second either sees the token already burnt by the first, or is
        retried by Odoo against the committed result once it can proceed.
        """
        sponsorship = cls._fetch_signup(sponsorship_id)
        sponsorship._my2_serialize_details_submission()
        if not sponsorship._my2_check_details_token(details_token):
            raise NotFound()
        return sponsorship

    @classmethod
    def _thank_you_values(
        cls,
        sponsorship,
        details_token=None,
        details_emailed=None,
        details_error=None,
        submitted=None,
    ):
        """Rendering context of the thank-you page, with or without the form.

        The token decides: empty means there is no form to offer, either
        because the details are already in or because this visitor never
        proved the signup is theirs.
        """
        token = False
        if sponsorship._my2_details_pending() and not details_emailed:
            if details_token and sponsorship._my2_check_details_token(details_token):
                # The emailed link carries its own proof. Handed straight
                # back to the form, never re-minted: the sponsor may still
                # need that same link a second time.
                token = details_token
            else:
                token = cls._issue_details_token(sponsorship)
        values = {
            "n_steps": _flow_n_steps(sponsorship),
            "sponsorship": sponsorship,
            # Gates the sponsor's name and email on the "All set" summary:
            # a bare sponsorship_id proves nothing (see _owns_signup), and
            # those are the only two fields on this public page that name a
            # real person rather than the sponsorship itself.
            "sponsor_identity_visible": cls._owns_signup(sponsorship),
            # Write credential of the post-payment details form. Minted
            # only for a visitor who proved they own this signup, never
            # off the id in the URL, and only while the signup is still
            # waiting for a name. Empty otherwise, which is what tells
            # the page it has no form to offer.
            "details_token": token,
            "details_emailed": bool(details_emailed),
            "details_error": details_error,
            "additional_title": _("Thank you"),
            # Public visitors have no session yet - the sign-in link they
            # were just emailed still has to run first, so this sends them
            # through the same login redirect "Go to my dashboard" uses,
            # just aimed at the letter editor instead of the dashboard.
            "first_letter_url": (
                "/web/login?"
                + urlencode(
                    {
                        "redirect": (
                            "/my2/children/letters/new"
                            f"?child_id={sponsorship.child_id.id}"
                        )
                    }
                )
            ),
        }
        if token:
            # What the sponsor typed wins over the prefill, so a submission
            # bounced for a missing field does not ask for the rest again.
            values.update(
                {
                    "details_prefill": {
                        **sponsorship._my2_details_prefill(),
                        **(submitted or {}),
                    },
                    "countries": request.env["res.country"].search([]),
                }
            )
        return values

    @staticmethod
    def _details_form_values(post):
        """The details form's submission, cleaned up.

        Whitespace-only is empty (an empty required field is the client's
        problem to report, not something to store), and the country is kept
        only if it names a real one - the id comes from the browser.
        """

        def text(key):
            return (post.get(key) or "").strip()

        country = request.env["res.country"].browse(safe_int(post.get("country")))
        return {
            "firstname": text("firstname"),
            "lastname": text("lastname"),
            "phone": text("phone"),
            "street": text("street"),
            "zip": text("zip"),
            "city": text("city"),
            "country_id": country.exists().id,
        }

    @staticmethod
    def _owns_signup(sponsorship):
        """Whether this visitor may act on this signup as its sponsor.

        Two proofs are accepted, and they are the two the design needs: the
        session that went through the checkout (the sponsor coming back from
        the gateway, same browser), and the authenticated sponsor. A bare
        sponsorship_id in the URL proves nothing on its own - ids are
        sequential and every route touching this signup is public.
        """
        owns_signup = sponsorship.id in (
            request.session.get(OWN_SIGNUPS_SESSION_KEY) or []
        )
        return owns_signup or MyCompassionSponsorshipPayment._is_sponsorship_user(
            sponsorship
        )

    @classmethod
    def _issue_details_token(cls, sponsorship):
        """Mint the details-form token, if this visitor may have one.

        The "do this later, we will email you" path does not come through
        here at all - it mints its token server-side into the email.
        """
        if not cls._owns_signup(sponsorship):
            return False
        return sponsorship._my2_ensure_details_token()

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
        # Model-side lookup: the same list feeds the dropdown of the
        # logged-in step and the buttons of the fast-checkout page.
        payment_methods = wizard._get_offered_payment_modes()
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
                # The step's own submit buttons, when it has any: one per
                # payment mode, in place of the generic Continue/Finish one.
                "payment_mode_buttons": wizard._get_payment_mode_buttons(),
                # Whether those buttons are this step's submit at all, which
                # is what says if the generic button may stand in when the
                # list above is empty.
                "step_offers_payment_modes": wizard._step_offers_payment_modes(),
            },
        )

        return html_content


class MyCompassionSponsorshipPayment(payment_portal.PaymentPortal):
    """First-payment checkout for sponsorships collected by an online
    payment provider. Extends PaymentPortal for the _create_transaction /
    _validate_transaction_kwargs helpers."""

    # by then any 3DS challenge is long expired. An unfinished checkout
    # transaction is cancelled so it stops blocking the first invoice.
    CHECKOUT_CLEANUP_MINUTES = 60

    @http.route(
        "/my2/new-sponsorship/payment",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def sponsorship_payment_page(
        self, sponsorship_id=None, access_token=None, **kwargs
    ):
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
        sponsorship = request.env["recurring.contract"].sudo().browse(sponsorship_id)
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
    def sponsorship_payment_transaction(
        self, sponsorship_id, access_token=None, **kwargs
    ):
        """Create the tokenizing first-payment transaction of a sponsorship,
        linked to its first invoice, and return its processing values."""
        sponsorship = self._fetch_guarded_sponsorship(sponsorship_id, access_token)
        provider = sponsorship.payment_mode_id.payment_provider_id
        if not provider or sponsorship.state not in ("draft", "waiting"):
            raise ValidationError(_("This sponsorship can no longer be paid online."))
        self._validate_transaction_kwargs(
            kwargs,
            additional_allowed_keys=(
                "reference_prefix",
                "currency_id",
                "partner_id",
            ),
        )
        if kwargs.get("flow") == "token" and not self._is_sponsorship_user(sponsorship):
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
            raise ValidationError(_("There is nothing to pay for this sponsorship."))
        # One charge request per invoice, like the cron and the update-card
        # page. The lock is taken before the decision so two clicks cannot
        # both pass.
        invoice._my2_serialize_charge_attempts()
        if invoice.transaction_ids.filtered(
            lambda t: t.state in ("draft", "pending", "authorized", "done")
        ):
            raise ValidationError(
                _("A payment is already in progress for this sponsorship.")
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
        ensure_recurring_instrument(tx_sudo)
        # An abandoned checkout would otherwise hold the payment-in-progress
        # guard above closed and the sponsor could never pay.
        tx_sudo.with_delay_sh(
            "_my2_cancel_stale_checkout_tx",
            eta=self.CHECKOUT_CLEANUP_MINUTES * 60,
            identity_key=f"sponsorship_checkout_cleanup.{tx_sudo.id}",
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
        # The context flag reaches the provider inline form rendering
        # through these recordsets. It tells _is_tokenization_required
        # that this checkout must save the card (see that method).
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
            "n_steps": _flow_n_steps(sponsorship),
            "reference_prefix": sponsorship.reference,
            "amount": invoice.amount_residual,
            "monthly_amount": sponsorship.total_amount,
            "currency": currency,
            "partner_id": partner.id,
            "providers_sudo": providers_sudo,
            "payment_methods_sudo": payment_methods_sudo,
            "tokens_sudo": tokens_sudo,
            "availability_report": {},
            "transaction_route": (f"/my2/new-sponsorship/transaction/{sponsorship.id}"),
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
