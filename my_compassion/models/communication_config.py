##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, fields, models

from .communication_job import NAMED_COMMUNICATION_MODELS


class CommunicationConfig(models.Model):
    _inherit = "partner.communication.config"

    my2_wait_for_name = fields.Boolean(
        "Wait for the donor's name",
        compute="_compute_my2_wait_for_name",
        store=True,
        readonly=False,
        help="A donor who gave only an email gets this communication once "
        'they give their name: it would greet them as "(pending)".',
    )

    @api.depends("model_id")
    def _compute_my2_wait_for_name(self):
        """By default the communications about invoices: thank-you letters
        and donation receipts."""
        for config in self:
            config.my2_wait_for_name = config.model in NAMED_COMMUNICATION_MODELS
