##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#    @author: Elias Keller <elias@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import math
from collections import defaultdict
from datetime import datetime, timedelta

from werkzeug.exceptions import BadRequest, NotFound

from odoo import fields, http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyCompassionDonationsController(CustomerPortal):
    @http.route(
        '/my2/gifts/<model("product.template"):product>',
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_donation_details_page(self, product, **kwargs):
        """
        Renders a donation details page for a specific donation (product).
        return: An HTTP response containing a rendered template with the donation
        details page.
        """
        sponsorships = request.env.user.partner_id.sponsorship_ids
        donation_limits = request.env["gift.threshold.settings"].sudo().search([])

        context = {
            "product": product,
            "sponsorships": sponsorships,
            "donation_limits": donation_limits,
        }

        return request.render(
            "my_compassion.my2_donation_details_page",
            context,
        )

    @http.route(
        "/my2/gifts/new",
        type="json",
        auth="user",
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
        product_template = (
            request.env["product.template"].sudo().browse(product_template_id)
        )

        # Make sure the product is available
        if not product_template.activate_for_my_compassion:
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

    @http.route(
        "/my2/gifts/edit",
        type="json",
        auth="user",
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

    @http.route(
        "/my2/gifts/get-limits",
        type="json",
        auth="user",
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
        product = request.env["product.template"].search([("id", "=", product_id)])
        if not product:
            return BadRequest()
        if sponsorship_id is not None:
            try:
                sponsorship_id = int(sponsorship_id)
            except TypeError as e:
                raise BadRequest() from e

        limits = product.get_donation_limits(
            request.website.company_id, request.env.user.partner_id, sponsorship_id
        )
        return limits

    @http.route(
        "/my2/gift-package",
        type="http",
        auth="user",
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
        request.session["sale_last_order_id"] = order.id

        # Fetch gift thresholds
        limits = request.env["gift.threshold.settings"].sudo().search([])

        # Fetch acquirer
        acquirer = self._get_payment_acquirer()

        return request.render(
            "my_compassion.my2_gift_package_page",
            {
                "order": order,
                "limits": limits,
                "acquirer": acquirer,
            },
        )

    @http.route(
        "/my2/gift-package/render-edit-form",
        type="json",
        auth="user",
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
            render_attrs["sponsorships"] = order_line.order_partner_id.sponsorship_ids
            render_attrs["default_sponsorship_id"] = order_line.gift_recipient_id.id

        # Render and return the form
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.DonationFormComponent", render_attrs
        )

        return {"html": html_content}

    @http.route(
        "/my2/gift-package/delete-item",
        type="json",
        auth="user",
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
        }

    @http.route(
        "/my2/gift-package/add",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_add_a_gift_page(self, **kwargs):
        """
        Renders the add a gift page to add a gift to the gift package.
        return: An HTTP response containing a rendered template with the add a
        gift page.
        """
        order = request.website.sale_get_order(force_create=True)
        products = request.env["product.template"].search(
            [
                ("activate_for_my_compassion", "=", True),
                "|",
                ("my_compassion_donation_type", "=", "gift"),
                ("my_compassion_donation_type", "=", "fund"),
            ]
        )

        sponsorships = request.env.user.partner_id.sponsorship_ids
        limits = request.env["gift.threshold.settings"].sudo().search([])

        return request.render(
            "my_compassion.my2_add_a_gift_page",
            {
                "products": products,
                "sponsorships": sponsorships,
                "limits": limits,
                "currency_name": order.pricelist_id.currency_id.name,
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
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = request.env["sale.order"].sudo().browse(sale_order_id)
            return request.render(
                "my_compassion.my2_gifts_thank_you_page",
                {"sale_order": sale_order},
            )
        return request.redirect("/my2/dashboard")

    @staticmethod
    def _extract_donation_order_line_fields(product_template, post):
        # Compute quantity
        price = 0
        amount = post.get("suggested_amount")
        if amount == "custom":
            try:
                price = float(post.get("custom_amount"))
            except (ValueError, TypeError) as e:
                raise BadRequest() from e
            # Make sure price is strictly positive
            if price <= 0:
                raise BadRequest()
        else:
            quantities = {
                "low": product_template.my_compassion_donation_quantity_low,
                "medium": product_template.my_compassion_donation_quantity_medium,
                "high": product_template.my_compassion_donation_quantity_high,
            }
            quantity = quantities.get(amount)
            if not quantity:
                raise BadRequest()
            price = quantity * product_template.list_price

        # Get frequency and force one_time for gifts
        if product_template.my_compassion_donation_type == "gift":
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
            "frequency": frequency,
        }
        if product_template.my_compassion_donation_type == "gift":
            order_line_fields["is_gift"] = True
            order_line_fields["gift_recipient_id"] = post.get("recipient")

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

        # Active sponsorships
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
            tot_cost_per_frequency[sponsorship.group_id.month_interval][
                currency
            ] += sponsorship.total_amount

        paid_invoices_data = self._get_paginated_paid_invoices(
            partner, invoice_page, invoice_per_page
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "active_sponsorships": active_sponsorships,
                "tot_cost_per_frequency": tot_cost_per_frequency,
                "due_invoices": due_invoices,
                "paid_invoices_subset": paid_invoices_data["paid_invoices_subset"],
                "current_page": paid_invoices_data["current_page"],
                "total_pages": paid_invoices_data["total_pages"],
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
        offset = (int(invoice_page) - 1) * invoice_per_page

        subset = self._get_paid_invoices_subset(partner, offset, invoice_per_page)

        total_amount = self._get_paid_invoices_amount(partner)

        total_pages = (
            math.ceil(total_amount / invoice_per_page) if invoice_per_page > 0 else 0
        )

        return {
            "paid_invoices_subset": subset,
            "current_page": int(invoice_page),
            "total_pages": total_pages,
        }

    @staticmethod
    def _get_payment_acquirer():
        return (
            http.request.env["payment.acquirer"]
            .sudo()
            .search([("provider", "=", "postfinance")], limit=1)
        )
