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
        translate=True,
        help="Target of the Policies link in the website footer, for the "
        "current language.",
    )
    footer_address = fields.Char(
        "Footer Address",
        translate=True,
        help="Address shown in the website footer for the current language. "
        "Falls back to the company's address when not set for a language.",
    )
    footer_phone = fields.Char(
        "Footer Phone",
        translate=True,
        help="Phone number shown in the website footer for the current "
        "language. Falls back to the company's phone when not set for a "
        "language.",
    )
    footer_company_ids = fields.Boolean(
        "Show Company IDs in Footer",
        help="Show the tax and registration numbers of the company (NIP and "
        "REGON for a Polish company) under the copyright line of the footer.",
    )
