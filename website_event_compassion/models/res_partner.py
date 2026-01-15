##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    registration_ids = fields.One2many(
        "event.registration",
        "partner_id",
        "Event registrations",
        readonly=False,
    )

    passport = fields.Binary(attachment=True)
    passport_name = fields.Char(compute="_compute_passport_name")

    def _compute_passport_name(self):
        for partner in self:
            if partner.passport:
                partner.passport_name = f"Passport_{partner.name}"
            else:
                partner.passport_name = False
