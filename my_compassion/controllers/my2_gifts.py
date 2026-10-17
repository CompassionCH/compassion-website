##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller <ekeller@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from urllib.parse import quote

from odoo import http
from odoo.http import request


class MyCompassionGiftController(http.Controller):
    @http.route("/my2/gifts", type="http", auth="public", website=True, sitemap=False)
    def render_donation_page(self, type="fund", **kwargs):
        """
        Renders a page of donation opportunities (Funds or Gifts).

        Funds are open to visitors, who give with their email only (see
        /my2/gift-package/donor); a gift goes to a sponsored child, so it
        needs the sponsor's account.

        :param type: 'fund' or 'gift', defaults to 'fund'.
        """
        if type not in ("fund", "gift"):
            type = "fund"
        if type == "gift" and request.env.user._is_public():
            return request.redirect(
                "/web/login?redirect=" + quote("/my2/gifts?type=gift")
            )

        domain = [
            ("activate_for_my_compassion", "=", True),
            ("my_compassion_donation_type", "=", type),
        ]

        # sudo: a visitor has no access to products; the domain is the gate,
        # and activate_for_my_compassion is read for the website's company.
        my_compassion_gifts = (
            request.env["product.template"]
            .sudo()
            .search(domain, order="website_sequence")
        )
        return request.render(
            "my_compassion.my2_gifts_page",
            {
                "my_compassion_gifts": my_compassion_gifts,
                "type": type,
            },
        )
