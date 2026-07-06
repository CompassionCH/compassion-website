##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    @api.model
    def get_current_website(self, fallback=True):
        # On the MyCompassion portal routes (/my2 and localized /<lang>/my2),
        # always resolve to the MyCompassion website so its theme applies even
        # when the page is reached from another website's link or domain.
        if request:
            path_parts = [p for p in request.httprequest.path.split("/") if p]
            is_my2_route = bool(path_parts) and (
                path_parts[0] == "my2"
                or (len(path_parts) > 1 and path_parts[1] == "my2")
            )
            if is_my2_route:
                target_website = self.env.ref(
                    "my_compassion.my2_website", raise_if_not_found=False
                )
                if target_website:
                    return target_website

        return super().get_current_website(fallback=fallback)
