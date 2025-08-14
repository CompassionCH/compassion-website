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
    def render_donation_page(self, type='fund', **kwargs):
        """
              Renders a page of donation opportunities (Funds or Gifts).
              :param donation_type: 'fund' or 'gift', defaults to 'fund'.
        """
        if type not in ('fund', 'gift'):
            type = 'fund'

        domain = [
            ('activate_for_my_compassion', '=', True),
            ('my_compassion_donation_type', '=', type),
        ]

        my_compassion_gifts = request.env['product.template'].search(domain)
        return request.render(
            "my_compassion.my2_fund_page",
            {
                'my_compassion_gifts': my_compassion_gifts,
                'type': type,
            })
