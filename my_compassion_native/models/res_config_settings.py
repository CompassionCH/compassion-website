##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    my2_bottom_nav_on_web = fields.Boolean(
        related="website_id.my2_bottom_nav_on_web",
        readonly=False,
    )
    # show only on mycompassion
    is_my_compassion = fields.Boolean(related="website_id.is_my_compassion")
