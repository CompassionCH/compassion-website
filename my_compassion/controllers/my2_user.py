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


class MyCompassionUserController(http.Controller):
    @http.route(
        "/my2/dashboard", type="http", auth="user", website=True, sitemap=False
    )
    def my2_render_dashboard_page(self, **kwargs):
        """
        Renders the dashboard page according to the logged-in user's role
        (sponsor, donor or volunteer).
        return: An HTTP response containing a rendered template with the dashboard.
        """

        partner = request.env.user.partner_id
        has_unread_correspondence = partner.has_unread_correspondence()

        return request.render("my_compassion.my2_dashboard_page", {
            "has_unread_correspondence": has_unread_correspondence,
            "partner": partner,
        })
