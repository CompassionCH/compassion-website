##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, fields, models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    is_my_compassion = fields.Boolean(
        "MyCompassion Website",
        help="This website runs the MyCompassion sponsor portal. A"
        " multi-company instance flags one website per country.",
    )
    data_change_notification_email = fields.Char(
        "Data Change Notification Email",
        help="Recipient of partner data-change notifications from the portal."
        " Defaults to the company email when empty.",
    )
    sponsor_child_url = fields.Char(
        "Sponsor a Child URL",
        help="Target of the 'start a sponsorship' link shown to users without"
        " sponsorships. Defaults to /my2/children when empty.",
    )

    @api.model
    def get_current_website(self, fallback=True):
        # On the MyCompassion portal routes (/my2 and localized /<lang>/my2),
        # resolve to a MyCompassion website so the portal theme applies even
        # when the page is reached from another website's link or domain. The
        # domain-matched website wins when it is itself a MyCompassion site
        # (multi-company instances run one per country); anything else falls
        # back to the default MyCompassion website.
        if request:
            path_parts = [p for p in request.httprequest.path.split("/") if p]
            is_my2_route = bool(path_parts) and (
                path_parts[0] == "my2"
                or (len(path_parts) > 1 and path_parts[1] == "my2")
            )
            if is_my2_route:
                domain_website = self.browse(
                    self.sudo()._get_current_website_id(
                        request.httprequest.host, fallback=False
                    )
                )
                if domain_website and domain_website.is_my_compassion:
                    return domain_website
                target_website = self.env.ref(
                    "my_compassion.my2_website", raise_if_not_found=False
                )
                if target_website:
                    return target_website
        return super().get_current_website(fallback=fallback)
