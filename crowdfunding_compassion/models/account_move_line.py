#    Copyright (C) 2020 Compassion CH
#    @author: Quentin Gigon

from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    crowdfunding_participant_id = fields.Many2one(
        "crowdfunding.participant",
        "Crowdfunding participant",
        domain=[
            ("project_id.state", "=", "active"),
            ("project_id.active", "=", True),
            ("project_id.deadline", ">=", fields.Date.today()),
        ],
        index=True,
    )
