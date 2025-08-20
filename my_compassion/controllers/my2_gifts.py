##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller <ekeller@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from urllib.parse import urljoin

from odoo import http
from odoo.http import request


class MyCompassionGiftController(http.Controller):
    @http.route("/my2/gifts", type="http", auth="user", website=True, sitemap=False)
    def render_donation_page(self, type="fund", **kwargs):
        """
        Renders a page of donation opportunities (Funds or Gifts).
        :param donation_type: 'fund' or 'gift', defaults to 'fund'.
        """
        if type not in ("fund", "gift"):
            type = "fund"

        base_url = request.httprequest.url_root

        page_content = {}
        if type == "gift":
            page_content = {
                "title": "Gift to your sponsored children",
                "description": (
                    "Send a gift to your sponsored child and Compassion staff from "
                    "their local church will support them in purchasing something "
                    "they really need."
                ),
                "banner_title": "Gift of compassion",
                "banner_text": (
                    "Every child deserves a secure home, safe water and medicine to "
                    "keep them healthy. That’s why when poverty places a child in "
                    "critical need, we take action."
                ),
                "banner_btn_text": "Send a gift",
                "banner_btn_link": urljoin(
                    base_url,
                    "/my2/gifts/?type=fund",
                ),
            }
        else:
            page_content = {
                "title": "Gift of compassion",
                "description": (
                    "Make a difference and bring hope to children living in extreme "
                    "poverty."
                ),
                "banner_title": "Give to your sponsored children",
                "banner_text": (
                    "Send a gift to your sponsored child. Compassion staff from "
                    "their local church will support them in purchasing something "
                    "they really need."
                ),
                "banner_btn_text": "Send a gift",
                "banner_btn_link": urljoin(
                    base_url,
                    "/my2/gifts/?type=gift",
                ),
            }

        domain = [
            ("activate_for_my_compassion", "=", True),
            ("my_compassion_donation_type", "=", type),
        ]

        my_compassion_gifts = request.env["product.template"].search(domain)
        return request.render(
            "my_compassion.my2_gifts_page",
            {
                "my_compassion_gifts": my_compassion_gifts,
                "page_content": page_content,
            },
        )
