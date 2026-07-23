##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    my2_bottom_nav_on_web = fields.Boolean(
        "Mobile app menu on web",
        help="Also show the mobile app bottom navigation on mobile browsers for "
        "this website, not only inside the native app. Off by default so the "
        "app shell stays native-only until a country opts in.",
    )
