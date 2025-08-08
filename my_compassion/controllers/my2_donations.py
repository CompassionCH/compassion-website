##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from time import sleep

from werkzeug.exceptions import NotFound, BadRequest

from odoo import http
from odoo.http import request


class MyCompassionDonationsController(http.Controller):
    @http.route(
        '/my2/donation-details/<model("product.template"):product>',
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

        # Only renders pages for product that are activated for MyCompassion
        if not product.activate_for_my_compassion:
            raise NotFound()

        return request.render(
            "my_compassion.my2_donation_details_page",
            {"product": product},
        )


    @http.route(
        '/my2/donation-details/submit',
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def donation_submit(self, **post):
        """
        Receives the donation submission and add it to the gift package of the user,
        then redirects to checkout (the gift package page).
        return: A redirection to the gift package page.
        """
        logging.info("====================================")
        logging.info(post)
        logging.info("------------------------------------")
        # {'product_id': '284', 'frequency': 'monthly', 'suggested_amount': 'custom', 'custom_amount': '100'}

        # Fetch the product record from the database
        product_template_id = int(post.get("product_id"))
        product_template = request.env["product.template"].sudo().browse(product_template_id)

        # Make sure the product is available
        if not product_template.activate_for_my_compassion:
            raise NotFound()

        # Compute quantity
        quantity = None
        amount = post.get("suggested_amount")
        if amount == 'low':
            quantity = product_template.my_compassion_donation_quantity_low
        elif amount == 'medium':
            quantity = product_template.my_compassion_donation_quantity_medium
        elif amount == 'high':
            quantity = product_template.my_compassion_donation_quantity_high
        elif amount == 'custom':
            # TODO: can fail
            custom_price = int(post.get('custom_amount'))
            quantity = custom_price / product_template.list_price
        else:
            raise BadRequest()

        # Get frequency
        # TODO: store frequency in the order line
        frequency = post.get('frequency')

        # Get current cart content
        order = request.website.sale_get_order(force_create=True)

        # Add product to the cart
        product = product_template.product_variant_id
        order.write({
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': quantity,
            })]
        })

        # Redirect to thank-you page
        return request.redirect("/my2/gift-package")


    @http.route(
        '/my2/gift-package',
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

        return request.render(
            "my_compassion.my2_gift_package_page",
            {
                'order': order,
              },
        )


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
        return: An JSON response containing the rendered template html.
        """
        order = request.website.sale_get_order()

        order_line_id = post.get('order_line_id')
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
                'order': order,
            },
        )

        return {"html": html_content}
