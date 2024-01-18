##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#    @author: Sebastien Toth <popod@me.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    registration_id = fields.Many2one(
        "event.registration",
        compute="_compute_registration",
        store=True,
        readonly=False,
    )

    @api.depends("ambassador_id.registration_ids", "origin_id.event_id")
    def _compute_registration(self):
        for contract in self:
            contract.registration_id = contract.ambassador_id.registration_ids.filtered(
                lambda r, c=contract: r.event_id == c.origin_id.event_id
            )
