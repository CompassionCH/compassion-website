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
        "/my2/dashboard/", type="http", auth="user", website=True, sitemap=False
    )
    def my2_render_dashboard_page(self, **kwargs):
        """
        Renders the dashboard page according to the logged-in user's role
        (sponsor, donor or volunteer).
        return: An HTTP response containing a rendered template with the dashboard.
        """
        partner = request.env.user.partner_id

        vignettes_data = [
            {
                "key": "sponsorship",
                "template": "my_compassion.dashboard_sponsorship_vignette",
                # Right now is_active is useless, but in the future it could be useful
                # if some vignettes don't have to be rendered
                "is_active": True,
                # High priority -> Shows first in page
                "priority": 2 + partner.is_sponsor * 100,
            },
            {
                "key": "donations",
                "template": "my_compassion.dashboard_donations_vignette",
                "is_active": True,
                "priority": 1 + partner.is_donor * 100,
            },
            {
                "key": "volunteering",
                "template": "my_compassion.dashboard_volunteering_vignette",
                "is_active": True,
                "priority": 0 + getattr(partner, "is_volunteer", False) * 100,
            },
        ]
        active_vignettes = [v for v in vignettes_data if v["is_active"]]
        sorted_vignettes = sorted(
            active_vignettes, key=lambda v: v["priority"], reverse=True
        )

        return request.render(
            "my_compassion.my2_dashboard_page",
            {
                "sorted_vignettes": sorted_vignettes,
            },
        )
