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

from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo import fields
from odoo.http import request
from collections import defaultdict
from datetime import datetime, timedelta
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

        return request.render(
            "my_compassion.my2_donation_details_page",
            {
                "product": product,
                "sponsorships": sponsorships,
            },
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

        # Get current cart content
        order = request.website.sale_get_order(force_create=True)

        # Add product to the cart
        order.write(
            {
                "order_line": [
                    (
                        0,
                        0,
                        self._extract_donation_order_line_fields(
                            product_template, post
                        ),
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
        # Get the current sales order
        order = request.website.sale_get_order()

        # Fetch gift thresholds
        limits = request.env["gift.threshold.settings"].sudo().search([])

        return request.render(
            "my_compassion.my2_gift_package_page",
            {
                "order": order,
                "limits": limits,
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

        render_attrs = {
            "product": order_line.product_template_id,
            "submit_label": "Ok",
            "default_frequency": order_line.frequency,
            "default_suggested_amount": "custom",
            "default_custom_amount": order_line.price_total,
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

        return {"html": html_content}

    @http.route(
        "/my2/gift-package/add",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_add_a_gift_page(self, **kwargs):
        """
        Renders the add a gift page to quickly add a gift to the gift package.
        return: An HTTP response containing a rendered template with the add a
        gift page.
        """
        # Exclude fund donation that are already in the user's gift package
        order = request.website.sale_get_order(force_create=True)
        product_template_ids_in_cart = order.order_line.product_id.product_tmpl_id.ids
        products = request.env["product.template"].search(
            [
                "&",
                ("activate_for_my_compassion", "=", True),
                "|",
                ("my_compassion_donation_type", "=", "gift"),
                ("id", "not in", product_template_ids_in_cart),
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
            current_partner = request.env.user.partner_id
            # Check that the order belongs to the current user
            if sale_order.partner_id == current_partner:
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

        # Get frequency
        frequency = post.get("frequency")

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
        ["/my2/my-donations"],
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

        # Computing the total price of the active sponsorships grouped per sponsorship frequency and payment method.
        # group_id groups the invoices that have the same payment method and frequency.
        tot_cost_per_frequency = defaultdict(lambda: defaultdict(float))

        for sponsorship in active_sponsorships:
            currency = sponsorship.pricelist_id.currency_id.name
            tot_cost_per_frequency[sponsorship.group_id.month_interval][
                currency
            ] += sponsorship.total_amount

        # redundant
        paid_invoices_offset = (invoice_page - 1) * invoice_per_page
        paid_invoices_subset = self._get_paid_invoices_subset(
            partner, paid_invoices_offset, invoice_per_page
        )
        total_paid_invoices = self._get_paid_invoices_amount(partner)
        total_pages = math.ceil(total_paid_invoices / invoice_per_page)

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "active_sponsorships": active_sponsorships,
                "tot_cost_per_frequency": tot_cost_per_frequency,
                "due_invoices": due_invoices,
                "paid_invoices_subset": paid_invoices_subset,
                "current_page": invoice_page,
                "total_pages": total_pages,
            }
        )
        return request.render("my_compassion.my2_my_donations_page", values)

    @http.route(
        "/my2/my-donations/history",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_donations_history(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Paid invoices
        paid_invoices_offset = (int(invoice_page) - 1) * invoice_per_page
        paid_invoices_subset = self._get_paid_invoices_subset(
            partner, paid_invoices_offset, invoice_per_page
        )

        # Paid invoices paging
        total_pages = (
            math.ceil(self._get_paid_invoices_amount(partner) / invoice_per_page)
            if invoice_per_page > 0
            else 0
        )

        history_data = {
            "current_page": int(invoice_page),
            "paid_invoices_subset": paid_invoices_subset,
            "total_pages": total_pages,
        }

        html = request.env["ir.qweb"]._render(
            "my_compassion.my2_donations_history_content",
            values=history_data,
        )

        return {"html": html}

