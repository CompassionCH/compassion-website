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


class MyCompassionFundController(http.Controller):
    @http.route(
        "/my2/gifts/", type="http", auth="user", website=True, sitemap=False
    )
    def my2_render_fund_page(self, **kwargs):
        """
        Renders the dashboard page according to the logged-in user's role
        (sponsor, donor or volunteer).
        return: An HTTP response containing a rendered template with the dashboard.
        """
        my_compassion_gifts = request.env['product.template'].search([
            ('activate_for_my_compassion', '=', True),
            ('my_compassion_donation_type', '=', 'fund'),
        ])
        return request.render(
            "my_compassion.my2_fund_page",
            {
                'my_compassion_gifts': my_compassion_gifts,
            })
