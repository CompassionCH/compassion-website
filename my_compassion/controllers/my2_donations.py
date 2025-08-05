##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request


class MyCompassionDonationsController(http.Controller):
    @http.route(
        '/my2/donation-details/<model("product.template"):product>',
        type="http", auth="user", website=True, sitemap=False
    )
    def my2_render_donation_details_page(self, product, **kwargs):
        """
        Renders a donation details page for a specific donation (product).
        return: An HTTP response containing a rendered template with the donation details page.
        """

        return request.render(
            "my_compassion.my2_donation_details_page",
            { "product": product },
        )