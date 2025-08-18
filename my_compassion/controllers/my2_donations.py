##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo.http import request


class MyCompassionDonationsController(http.Controller):
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
        return: An HTTP response containing a rendered template with the donation details page.
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
        except (ValueError, TypeError):
            raise BadRequest()
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
        # Fetch the order line record from the database
        order_line_id = post.get("order_line_id")
        order_line = request.env["sale.order.line"].sudo().browse(order_line_id)

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
        return: An HTTP response containing a rendered template with the gift package page.
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
        "/my2/gifts/thankyou",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_gifts_thank_you_page(self, **kwargs):
        sale_order_id = int(kwargs.get("sale_order_id", 0))
        if not sale_order_id:
            raise NotFound("Sale order ID has not been found")

        # TODO: add the partner_id check here to make sure the user is allowed to see this order
        sale_order = (
            request.env["sale.order"]
            .sudo()
            .search(
                [
                    ("id", "=", sale_order_id),
                ]
            )
        )

        return request.render(
            "my_compassion.my2_gifts_thank_you_page",
            {
                "sale_order": sale_order,
            },
        )

    @staticmethod
    def _extract_donation_order_line_fields(product_template, post):
        # Compute quantity
        price = 0
        amount = post.get("suggested_amount")
        if amount == "low":
            price = (
                product_template.my_compassion_donation_quantity_low
                * product_template.list_price
            )
        elif amount == "medium":
            price = (
                product_template.my_compassion_donation_quantity_medium
                * product_template.list_price
            )
        elif amount == "high":
            price = (
                product_template.my_compassion_donation_quantity_high
                * product_template.list_price
            )
        elif amount == "custom":
            try:
                price = float(post.get("custom_amount"))
            except (ValueError, TypeError):
                raise BadRequest()
            # Make sure price is strictly positive
            if price <= 0:
                raise BadRequest()
        else:
            raise BadRequest()

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
