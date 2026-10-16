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
                lambda r, c=contract: r.compassion_event_id == c.origin_id.event_id
            )

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        contracts._source_from_registration()
        return contracts

    def write(self, vals):
        res = super().write(vals)
        if {"ambassador_id", "origin_id", "registration_id"} & set(vals):
            self._source_from_registration()
        return res

    def _source_from_registration(self):
        """A sponsorship brought by a fundraiser gets the source of the
        fundraiser, unless it has a source other than the one of its origin
        (or unknown)."""
        for contract in self:
            source = contract.registration_id.source_id
            if source and contract._follows_origin("source_id"):
                contract.source_id = source
