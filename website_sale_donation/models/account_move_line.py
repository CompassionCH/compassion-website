from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    is_anonymous = fields.Boolean(
        help="Should the donation be anonymous?", default=False
    )
