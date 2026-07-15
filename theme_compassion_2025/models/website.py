##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    social_vimeo = fields.Char("Vimeo Account")
    privacy_policy_url = fields.Char(
        "Privacy Policy URL",
        help="Target of the Policies link in the website footer.",
    )
