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
        vignettes_data = self._get_vignettes(partner)

        return request.render(
            "my_compassion.my2_dashboard_page",
            {
                "sorted_vignettes": vignettes_data,
                "partner": partner,
            },
        )

    def _get_vignettes(self, partner):
        vignettes = [
            {
                "key": "sponsorship",
                "template": "my_compassion.dashboard_sponsorship_vignette",
                # Low priority number -> Shows first in page
                "priority": 0 - partner.is_sponsor * 100,
                "number_sponsorships": partner.number_sponsorships,
            },
            {
                "key": "donations",
                "template": "my_compassion.dashboard_donations_vignette",
                "priority": 1 - partner.is_donor * 100,
            },
            {
                "key": "volunteering",
                "template": "my_compassion.dashboard_volunteering_vignette",
                "priority": 2 - getattr(partner, "is_volunteer", False) * 100,
            },
        ]
        return sorted(vignettes, key=lambda v: v["priority"])
