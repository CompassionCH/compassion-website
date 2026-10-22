##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#    @author: Elias Keller <elias@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import quote

from werkzeug.exceptions import BadRequest, NotFound

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import email_normalize
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.sale.controllers import portal as sale_portal

from .website_utils import safe_int

_logger = logging.getLogger(__name__)

# Donors a visitor's session may create within an hour (see the email step).
MAX_DONORS_PER_SESSION = 5


class MyCompassionDonationsController(CustomerPortal):
    @http.route(
        "/my2/gifts/<int:product_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_render_donation_details_page(self, product_id, **kwargs):
        """
        Renders a donation details page for a specific donation (product).
        A visitor may open a fund, not a gift (see _get_donation_product).
        return: An HTTP response containing a rendered template with the donation
        details page.
        """
        product = self._get_donation_product(product_id)
        if not product:
            if request.env.user._is_public():
                return request.redirect(
                    "/web/login?redirect=" + quote(f"/my2/gifts/{product_id}")
                )
            raise NotFound()
        sponsorships = self._get_gift_eligible_sponsorships(request.env.user.partner_id)
        donation_limits = request.env["gift.threshold.settings"].sudo().search([])

        context = {
            "product": product,
            "sponsorships": sponsorships,
            "donation_limits": donation_limits,
            "additional_title": "{} - {}".format(
                _("Gifts"), product.my_compassion_name
            ),
        }

        return request.render(
            "my_compassion.my2_donation_details_page",
            context,
        )

    @http.route(
        "/my2/gifts/<string:slug>-<int:product_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_redirect_slugged_donation_page(self, slug, product_id, **kwargs):
        """Links with the product's slug (/my2/gifts/<name>-<id>, the form the
        details page had) lead to the details page."""
        if not self._get_donation_product(product_id):
            raise NotFound()
        return request.redirect(f"/my2/gifts/{product_id}", code=301)

    @http.route(
        "/my2/gifts/new",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def donation_new(self, **post):
        """
        Receives the donation submission and add it to the gift package of the user,
        then redirects to checkout (the gift package page).
        """
        # Fetch the product record from the database
        try:
            product_template_id = int(post.get("product_id"))
        except (ValueError, TypeError) as e:
            raise BadRequest() from e
        # Make sure the product is available (to this visitor)
        product_template = self._get_donation_product(product_template_id)
        if not product_template:
            raise NotFound()
        # Extract order line for the current product
        current_order_line_fields = self._extract_donation_order_line_fields(
            product_template, post
        )
        # Get current cart content
        order = request.website.sale_get_order(force_create=True)
        # See if an existing row for the same product and the same sponsorship exists
        # If it's the case, just increment the amount of the donation
        domain = [
            ("order_id", "=", order.id),
            ("product_id.product_tmpl_id", "=", product_template.id),
            ("frequency", "=", current_order_line_fields.get("frequency")),
        ]
        if current_order_line_fields.get("is_gift") and current_order_line_fields.get(
            "gift_recipient_id"
        ):
            domain.append(
                (
                    "gift_recipient_id",
                    "=",
                    int(current_order_line_fields.get("gift_recipient_id")),
                )
            )
        # Order lines for the same product (same sponsorship, same product)
        matching_lines = request.env["sale.order.line"].sudo().search(domain)

        # Aggregate the matching lines if necessary
        if matching_lines:
            aggregated_line = matching_lines[0]
            aggregated_price = sum(line.price_unit for line in matching_lines)

            # Unlink all but the first one in a single call
            if len(matching_lines) > 1:
                matching_lines[1:].unlink()

            # Add to the aggregated price the one of the current donation
            aggregated_price += current_order_line_fields["price_unit"]
            aggregated_line.price_unit = aggregated_price

        else:
            # Add the new product to the cart
            order.write(
                {
                    "order_line": [
                        (
                            0,
                            0,
                            current_order_line_fields,
                        )
                    ]
                }
            )
        request.session["website_sale_cart_quantity"] = order.cart_quantity

    @http.route(
        "/my2/gifts/edit",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def donation_edit(self, **post):
        """
        Edits a donation from the user's gift package.
        """
        # Fetch the order line record from the user's cart
        order = request.website.sale_get_order()
        order_line_id = post.get("order_line_id")
        order_line = order and order.order_line.filtered(
            lambda line: line.id == order_line_id
        )

        # Make sure the order line exists
        if not order_line:
            raise NotFound()

        product_template = order_line.product_template_id

        order_line.write(
            self._extract_donation_order_line_fields(product_template, post)
        )
        request.session["website_sale_cart_quantity"] = (
            order.cart_quantity if order else 0
        )

    @http.route(
        "/my2/gifts/get-limits",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def donation_get_limits(self, product_id, sponsorship_id=None, **post):
        """
        Returns the donation limits for a product (and optionally a sponsorship)
        in the form:
        {
            "min_amount": int,               # If amount is limited
            "max_amount": int,               # If amount is limited
            "remaining_donations": int,      # If frequency is limited
        }
        """
        try:
            product_id = int(product_id)
        except (TypeError, ValueError) as e:
            raise BadRequest() from e
        product = self._get_donation_product(product_id)
        if not product:
            raise BadRequest()
        if sponsorship_id is not None:
            try:
                sponsorship_id = int(sponsorship_id)
            except (TypeError, ValueError) as e:
                raise BadRequest() from e

        # sudo: the donor may belong to another company, and the limits are
        # converted to the currency of the website's company.
        limits = product.get_donation_limits(
            request.website.company_id.sudo(),
            request.env.user.partner_id,
            sponsorship_id,
            request.website.sale_get_order(),
        )
        minimum = self._my2_min_amount(product)
        if minimum and minimum > (limits.get("min_amount") or 0):
            limits["min_amount"] = minimum
        return limits

    @staticmethod
    def _my2_min_amount(product):
        """The smallest amount a donor may give to this fund on this website."""
        if product.my_compassion_donation_type != "fund":
            return 0.0
        return request.website.my2_min_donation_amount

    @http.route(
        "/my2/gift-package",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_render_gift_package_page(self, **kwargs):
        """
        Renders the gift package (cart) page.
        return: An HTTP response containing a rendered template with the gift
        package page.
        """
        # Get the current sales order and register it as last order
        # (usually done in a confirmation step that we don't have)
        order = request.website.sale_get_order()
        if order:
            request.session["sale_last_order_id"] = order.id

        # Fetch gift thresholds
        limits = request.env["gift.threshold.settings"].sudo().search([])

        # Payment form context for the embedded standard payment form. The
        # landing route confirms the order and redirects to /shop/confirmation;
        # on a MyCompassion website that route is overridden to redirect to the
        # branded /my2/gifts/thankyou page.
        payment_form_values = {}
        donor_values = self._get_donor_step_values(order, **kwargs)
        if order and order.order_line and not donor_values.get("donor_needed"):
            payment_form_values = {
                **sale_portal.CustomerPortal._get_payment_values(
                    self, order.sudo(), website_id=request.website.id
                ),
                "transaction_route": f"/shop/payment/transaction/{order.id}",
                "landing_route": "/shop/payment/validate",
                "sale_order_id": order.id,
            }
            if request.env.user._is_public():
                # The cart's partner comes from an email anyone may type: its
                # saved cards are never offered to a visitor (and a saved card
                # sent all the same is refused, see MyCompassionShopPayment).
                payment_form_values["tokens_sudo"] = request.env["payment.token"].sudo()

        return request.render(
            "my_compassion.my2_gift_package_page",
            {
                "order": order,
                "limits": limits,
                "payment_failed": bool(kwargs.get("payment_failed")),
                **donor_values,
                **payment_form_values,
            },
        )

    @http.route(
        "/my2/gift-package/donor",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        sitemap=False,
    )
    def my2_gift_package_donor(self, email=None, privacy_consent=None, **post):
        """Who gives, for a visitor: their email and privacy consent only, as
        the sponsorship fast checkout asks. The donor is created with the
        same placeholder name; the real one comes from the payment (the name
        on the card) or from the form of the thank-you page.

        No partner exists before this step, so a cart filled by a robot
        creates none. The donor created here may change their email while
        nobody else can own it (_my2_donor_is_visitor_only); otherwise a new
        donor is created: the email of a partner that became someone's
        account (signup links an account to a partner of the same email) is
        never rewritten from a visitor's session.
        """
        if not request.env.user._is_public():
            return request.redirect("/my2/gift-package")
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect("/my2/gift-package")
        normalized = email_normalize(email or "")
        if not normalized or not privacy_consent:
            return request.redirect("/my2/gift-package?donor_error=1")
        if not self._my2_donor_step_allowed():
            return request.redirect("/my2/gift-package?donor_error=verify")

        order = order.sudo()
        # A double click must not make two donors: the second request waits,
        # then is replayed and finds the donor of the first one.
        request.env.cr.execute(
            "SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE", [order.id]
        )
        partner = self._get_session_donor(order)
        if partner and partner.email == normalized:
            pass
        elif partner and self._my2_donor_is_visitor_only(partner, order):
            partner.email = normalized
        else:
            partner = self._my2_reusable_donor(order, normalized)
            if not partner:
                company = request.website.company_id
                partner = (
                    request.env["res.partner"]
                    .sudo()
                    .create(
                        {
                            "lastname": request.env["res.partner"].MY2_PLACEHOLDER_NAME,
                            "firstname": False,
                            "my2_name_placeholder": True,
                            "my2_email_unverified": True,
                            "email": normalized,
                            "lang": request.lang.code,
                            "country_id": company.country_id.id,
                            "legal_agreement_date": fields.Datetime.now(),
                        }
                    )
                )
                request.session["my2_donors_created"] = [
                    *self._my2_recent_donors_created(),
                    fields.Datetime.now().timestamp(),
                ]
            # The pricelist is written back with the partner: changing the
            # partner would recompute it, and with it the amounts the donor
            # chose.
            order.write(
                {
                    "partner_id": partner.id,
                    "partner_invoice_id": partner.id,
                    "partner_shipping_id": partner.id,
                    "pricelist_id": order.pricelist_id.id,
                }
            )
            request.session["my2_donor_partner_id"] = partner.id
        return request.redirect("/my2/gift-package")

    def _my2_reusable_donor(self, order, email):
        """A donor this session already made, with the same email, that is
        still nobody's account: the donor of an earlier donation of the
        session, or the cart's own donor (a replayed double click). Never a
        partner found by its email alone: an unverified email must not attach
        a donation to someone else."""
        Partner = request.env["res.partner"].sudo()
        candidates = Partner.browse(
            [
                request.session.get("my2_donor_partner_id"),
                order.partner_id.id
                if order.partner_id != request.website.partner_id
                else None,
            ]
        )
        for partner in candidates.exists():
            if (
                partner.email == email
                and not partner.with_context(active_test=False).user_ids
            ):
                return partner
        return Partner

    def _my2_donor_step_allowed(self):
        """A human, and not too many donors from this session: the email step
        is the gate of public payments, which card testers would automate.
        The reCAPTCHA check passes while no reCAPTCHA key is configured."""
        if len(self._my2_recent_donors_created()) >= MAX_DONORS_PER_SESSION:
            return False
        try:
            return request.env["ir.http"]._verify_request_recaptcha_token("my2_donor")
        except (UserError, ValidationError):
            return False

    @staticmethod
    def _my2_recent_donors_created():
        since = fields.Datetime.now().timestamp() - 3600
        return [t for t in request.session.get("my2_donors_created", []) if t > since]

    @http.route(
        "/my2/gift-package/render-edit-form",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def render_edit_form(self, **post):
        """
        Renders the edit form template for the given order line and returns it as HTML.
        return: A JSON response containing the rendered template html.
        """
        order = request.website.sale_get_order()

        order_line_id = post.get("order_line_id")
        order_line = order.order_line.filtered(lambda line: line.id == order_line_id)
        if not order_line:
            raise NotFound()

        limits = request.env["gift.threshold.settings"].sudo().search([])

        render_attrs = {
            "product": order_line.product_template_id,
            "submit_label": "Ok",
            "default_frequency": order_line.frequency,
            "default_suggested_amount": "custom",
            "default_custom_amount": order_line.price_total,
            "limits": limits,
            "date": fields.Date.today(),
            "currency_name": order.pricelist_id.currency_id.name,
        }

        if order_line.is_gift:
            render_attrs["sponsorships"] = self._get_gift_eligible_sponsorships(
                request.env.user.partner_id
            )
            render_attrs["default_sponsorship_id"] = order_line.gift_recipient_id.id

        # Render and return the form
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.DonationFormComponent", render_attrs
        )

        return {"html": html_content}

    @http.route(
        "/my2/gift-package/delete-item",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def remove_item(self, **post):
        """
        Deletes an item from the user's gift package
        and renders the new gift package content using the
        my_compassion.my2_gift_package_content template.
        return: A JSON response containing the rendered template html.
        """
        order = request.website.sale_get_order()

        order_line_id = post.get("order_line_id")
        order_line = order.order_line.filtered(lambda line: line.id == order_line_id)
        if order_line:
            # Delete the record
            order_line.unlink()
        else:
            raise NotFound()

        cart_quantity = order.cart_quantity
        request.session["website_sale_cart_quantity"] = cart_quantity

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_gift_package_content",
            {
                "order": order,
            },
        )

        return {
            "html": html_content,
            "is_order_empty": len(order.order_line) == 0,
            "cart_quantity": cart_quantity,
        }

    @http.route(
        "/my2/gift-package/add",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_render_add_a_gift_page(self, **kwargs):
        """
        Renders the add a gift page to add a gift to the gift package.
        return: An HTTP response containing a rendered template with the add a
        gift page.
        """
        donation_types = ["fund"] if request.env.user._is_public() else ["gift", "fund"]
        products = request.website._my2_donation_products(
            [("my_compassion_donation_type", "in", donation_types)]
        )

        sponsorships = self._get_gift_eligible_sponsorships(request.env.user.partner_id)
        limits = request.env["gift.threshold.settings"].sudo().search([])

        return request.render(
            "my_compassion.my2_add_a_gift_page",
            {
                "products": products,
                "sponsorships": sponsorships,
                "limits": limits,
            },
        )

    @http.route(
        "/my2/gifts/thankyou",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_gifts_thank_you_page(self, **kwargs):
        sale_order = (
            request.env["sale.order"]
            .sudo()
            .browse(request.session.get("sale_last_order_id"))
            .exists()
        )
        if sale_order.website_id == request.website:
            outcome = sale_order._my2_payment_outcome()
            if outcome == "paid":
                return request.render(
                    "my_compassion.my2_gifts_thank_you_page",
                    {
                        "sale_order": sale_order,
                        **self._get_donor_details_values(sale_order, **kwargs),
                    },
                )
            # website_sale sends a cancelled or refused payment here too, and
            # empties the cart first (sale_reset): give the cart back and let
            # the donor try again instead of thanking them.
            if sale_order.state in ("draft", "sent"):
                if sale_order.state == "sent":
                    # website_sale only takes a draft quotation as a cart.
                    sale_order.action_draft()
                request.session["sale_order_id"] = sale_order.id
                request.session["website_sale_cart_quantity"] = sale_order.cart_quantity
            if outcome == "failed":
                return request.redirect("/my2/gift-package?payment_failed=1")
            return request.redirect("/my2/gift-package")
        if request.env.user._is_public():
            return request.redirect("/my2/gifts")
        return request.redirect("/my2/dashboard")

    @http.route(
        "/my2/gifts/thankyou/details",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        sitemap=False,
    )
    def my2_gifts_thank_you_details(self, firstname=None, lastname=None, **post):
        """The name of a visitor whose payment did not tell it.

        Only the session that paid may write it, and only over the
        placeholder: a real name, typed here or reported by the payment, is
        never overwritten (_my2_replace_placeholder_name).
        """
        sale_order = (
            request.env["sale.order"]
            .sudo()
            .browse(request.session.get("sale_last_order_id"))
            .exists()
        )
        partner = self._get_session_donor(sale_order).filtered("my2_name_placeholder")
        firstname, lastname = (firstname or "").strip(), (lastname or "").strip()
        if not partner:
            return request.redirect("/my2/gifts/thankyou")
        if not firstname or not lastname:
            return request.redirect("/my2/gifts/thankyou?details_error=1")
        partner._my2_replace_placeholder_name(firstname, lastname)
        return request.redirect("/my2/gifts/thankyou")

    @http.route(
        "/my2/payment/status",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def my2_payment_status(self, **post):
        """Live status of the donor's last payment, for the mobile app.

        The payment runs in an external browser whose session Odoo never sees,
        so the app polls this instead of being told how it went (T3378). Ask
        the gateway directly rather than waiting for the sweep.
        """
        tx = (
            request.env["payment.transaction"]
            .sudo()
            .browse(request.session.get(PaymentPostProcessing.MONITORED_TX_ID_KEY))
            .exists()
        )
        if (
            not tx
            or tx.partner_id != request.env.user.partner_id
            or tx.provider_code != "postfinance"
        ):
            return {"state": False}

        seconds_ago = int((fields.Datetime.now() - tx.create_date).total_seconds())
        if not tx.provider_reference:
            # PostFinance refused to create the payment, so there is nothing to
            # poll: tell the app instead of spinning forever (T3472).
            return {
                "state": "error",
                "seconds_ago": seconds_ago,
                "processing": False,
                "reference": tx.reference,
            }

        # Only chase a payment that can still move, and only a recent one.
        recent = tx.create_date > fields.Datetime.subtract(
            fields.Datetime.now(), hours=2
        )
        if recent and tx.state not in ("done", "cancel", "error"):
            try:
                tx._process_notification_data({})
                if tx.state == "done" and not tx.is_post_processed:
                    tx._post_process()
            except Exception:
                # A payment that cannot be post-processed is still a payment:
                # report the state so the app stops asking for money.
                _logger.exception(
                    "Could not refresh PostFinance transaction %s", tx.reference
                )

        return {
            "state": tx.state,
            "seconds_ago": seconds_ago,
            "processing": tx.state in ("draft", "pending"),
            "reference": tx.reference,
        }

    def _get_donation_product(self, product_id):
        """The donation product a visitor or user may give to, or an empty
        recordset.

        The gate, read in sudo (a visitor has no access to products):
        published on MyCompassion by the website's company and active
        (website._my2_donation_products), sold (with a variant to put in the
        cart), and a fund for a visitor - a gift goes to a sponsored child,
        which takes an account.
        """
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return request.env["product.template"]
        product = request.website._my2_donation_products([("id", "=", product_id)])
        if not (product.sale_ok and product.product_variant_id):
            return request.env["product.template"]
        if (
            request.env.user._is_public()
            and product.my_compassion_donation_type != "fund"
        ):
            return request.env["product.template"]
        return product

    def _get_session_donor(self, order):
        """The donor this visitor's session created for order, or an empty
        recordset: the only partner a visitor may write to.

        Still theirs once named (the name may be typed while the payment is
        pending): a refused payment then gives the cart back to the same
        donor, never to a second one. Only the name requires the placeholder.
        """
        partner = request.env["res.partner"].sudo()
        donor_id = request.session.get("my2_donor_partner_id")
        if not order or not donor_id or order.partner_id.id != donor_id:
            return partner
        return partner.browse(donor_id).exists()

    @staticmethod
    def _my2_donor_is_visitor_only(partner, order):
        """Whether the donor of a visitor's cart is still theirs alone: no
        account, still the placeholder name, and nothing but this cart - no
        other order, invoice, saved card or payment."""
        if partner.user_ids or not partner.my2_name_placeholder:
            return False
        env = partner.env
        others = (
            ("sale.order", [("id", "!=", order.id)]),
            ("account.move", []),
            ("payment.token", []),
            (
                "payment.transaction",
                [("state", "in", ("pending", "authorized", "done"))],
            ),
        )
        return not any(
            env[model]
            .with_context(active_test=False)
            .search_count([("partner_id", "=", partner.id), *domain], limit=1)
            for model, domain in others
        )

    def _get_donor_step_values(self, order, **kwargs):
        """What the gift package page shows a visitor before the payment
        form: the email step while the cart is still the public user's, and
        the email the receipt goes to once given (with a way to change it)."""
        if not request.env.user._is_public() or not order:
            return {}
        donor = self._get_session_donor(order.sudo())
        change = kwargs.get("change_donor") and donor
        return {
            "donor_needed": bool(order.order_line) and (not donor or change),
            "donor_email": donor.email if donor else "",
            "donor_error": kwargs.get("donor_error"),
        }

    def _get_donor_details_values(self, sale_order, **kwargs):
        """The name form of the thank-you page, for the visitor whose payment
        did not tell their name (BLIK, PostFinance...)."""
        donor = self._get_session_donor(sale_order)
        if not donor.my2_name_placeholder:
            return {}
        cardholder = (
            (
                sale_order.transaction_ids.filtered(lambda t: t.state == "done")[:1]
            ).my2_cardholder_name
            or ""
        )
        firstname, lastname = (
            payment_utils.split_partner_name(cardholder) if cardholder else ("", "")
        )
        return {
            "donor_details_needed": True,
            "donor_details_prefill": {"firstname": firstname, "lastname": lastname},
            "donor_details_error": bool(kwargs.get("details_error")),
        }

    def _get_gift_eligible_sponsorships(self, partner):
        """Sponsorships that can receive a gift."""
        return partner.sponsorship_ids.filtered(
            lambda s: s.can_show_on_my_compassion
            and (
                s.state != "terminated"
                or s.can_write_letter
                or not s.exit_communication_sent
            )
        )

    def _extract_donation_order_line_fields(self, product_template, post):
        # Compute quantity
        price = 0
        amount_type = post.get("suggested_amount")
        if amount_type == "custom":
            try:
                price = float(post.get("custom_amount"))
            except (ValueError, TypeError) as e:
                raise BadRequest() from e
            # Make sure price is strictly positive
            if price <= 0:
                raise BadRequest()
        else:
            amounts = {
                "low": product_template.my_compassion_donation_amount_low,
                "medium": product_template.my_compassion_donation_amount_medium,
                "high": product_template.my_compassion_donation_amount_high,
            }
            price = amounts.get(amount_type)

            if price is None or price <= 0:
                raise BadRequest()
        if price < self._my2_min_amount(product_template):
            raise BadRequest()

        # Get frequency and force one_time for gifts, and for visitors: a
        # monthly donation needs a payment instrument kept for an account.
        if (
            product_template.my_compassion_donation_type == "gift"
            or request.env.user._is_public()
        ):
            frequency = "one_time"
        else:
            frequency = post.get("frequency")
            if frequency not in ("one_time", "monthly"):
                raise BadRequest(
                    "A valid frequency is required for this type of donation."
                )

        product = product_template.product_variant_id
        order_line_fields = {
            "product_id": product.id,
            "price_unit": price,
            "product_uom_qty": 1.0,
            "frequency": frequency,
        }
        if product_template.my_compassion_donation_type == "gift":
            try:
                recipient_id = int(post.get("recipient"))
            except (ValueError, TypeError) as e:
                raise BadRequest() from e
            eligible = self._get_gift_eligible_sponsorships(request.env.user.partner_id)
            if recipient_id not in eligible.ids:
                raise BadRequest()
            order_line_fields["is_gift"] = True
            order_line_fields["gift_recipient_id"] = recipient_id

        return order_line_fields

    def _get_paid_invoices_filter(self, partner):
        paid_invoices_filter = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]
        return paid_invoices_filter

    def _get_paid_invoices_subset(self, partner, offset, amount):
        paid_invoices_subset = (
            request.env["account.move"]
            .sudo()
            .search(
                self._get_paid_invoices_filter(partner),
                offset=offset,
                limit=amount,
                order="last_payment desc",
            )
        )
        return paid_invoices_subset

    def _get_paid_invoices_amount(self, partner):
        number_of_paid_invoices = (
            request.env["account.move"]
            .sudo()
            .search_count(self._get_paid_invoices_filter(partner))
        )
        return number_of_paid_invoices

    @http.route(
        "/my2/donations",
        type="http",
        auth="user",
        website=True,
    )
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Active sponsorships (terminated departures stay listed until the
        # exit communication has been sent)
        active_sponsorships = partner.get_portal_sponsorships("active")

        # Due invoices
        date_filter_up_bound = datetime.today() + timedelta(days=30)
        due_invoices = (
            request.env["account.move"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("payment_state", "=", "not_paid"),
                    ("invoice_category", "=", "sponsorship"),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("amount_total", "!=", 0),
                    ("invoice_date", "<", fields.Date.to_string(date_filter_up_bound)),
                ]
            )
        )

        # Computing the total price of the active sponsorships grouped
        # per sponsorship frequency and payment method.
        # group_id groups the invoices that have the same payment method and frequency.
        tot_cost_per_frequency = defaultdict(lambda: defaultdict(float))

        for sponsorship in active_sponsorships:
            currency = sponsorship.pricelist_id.currency_id.name
            tot_cost_per_frequency[sponsorship.group_id.month_interval][currency] += (
                sponsorship.total_amount
            )

        paid_invoices_data = self._get_paginated_paid_invoices(
            partner, invoice_page, invoice_per_page
        )

        # The tax-receipt year selector needs the year span of the partner's
        # paid invoices, independent of any country layer extending this portal.
        first_paid_date = (
            request.env["account.move"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("payment_state", "=", "paid"),
                    ("move_type", "=", "out_invoice"),
                    ("amount_total", ">", 0),
                ],
                limit=1,
                order="create_date asc",
            )
            .create_date
        )
        current_year = datetime.today().year

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "active_sponsorships": active_sponsorships,
                "tot_cost_per_frequency": tot_cost_per_frequency,
                "due_invoices": due_invoices,
                "paid_invoices_subset": paid_invoices_data["paid_invoices_subset"],
                "current_page": paid_invoices_data["current_page"],
                "total_pages": paid_invoices_data["total_pages"],
                "additional_title": _("My Donations"),
                "current_year": current_year,
                "first_year": first_paid_date.year if first_paid_date else current_year,
            }
        )
        return request.render("my_compassion.my2_my_donations_page", values)

    @http.route(
        "/my2/donations/history",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_donations_history(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        history_data = self._get_paginated_paid_invoices(
            partner, invoice_page, invoice_per_page
        )

        html = request.env["ir.qweb"]._render(
            "my_compassion.my2_donations_history_content",
            values=history_data,
        )

        return {"html": html}

    def _get_paginated_paid_invoices(
        self, partner, invoice_page=1, invoice_per_page=12
    ):
        """
        Fetches a paginated subset of paid invoices for a partner and calculates
        pagination details.
        """
        invoice_page = max(1, safe_int(invoice_page, 1))
        invoice_per_page = max(1, safe_int(invoice_per_page, 12))
        offset = (invoice_page - 1) * invoice_per_page

        subset = self._get_paid_invoices_subset(partner, offset, invoice_per_page)

        total_amount = self._get_paid_invoices_amount(partner)

        total_pages = (
            math.ceil(total_amount / invoice_per_page) if invoice_per_page > 0 else 0
        )

        return {
            "paid_invoices_subset": subset,
            "current_page": invoice_page,
            "total_pages": total_pages,
        }
