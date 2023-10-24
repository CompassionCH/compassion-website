##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class WebsiteSponsorship(models.TransientModel):
    _inherit = "cms.form.sponsorship"

    registration_id = fields.Many2one("event.registration")

    def _get_sponsorship_vals(self):
        vals = super()._get_sponsorship_vals()
        vals["ambassador_id"] = self.registration_id.partner_id.id
        vals["origin_id"] = self.registration_id.compassion_event_id.origin_id.id
        return vals
