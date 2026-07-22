from odoo import fields, models


class PaymentMode(models.Model):
    _inherit = [
        "account.payment.mode",
        "website.published.mixin",
    ]
    _name = "account.payment.mode"

    payment_provider_id = fields.Many2one(
        "payment.provider",
        string="Online payment provider",
        check_company=True,
        help="If set, invoices collected through this mode are charged off-session "
        "against the sponsor's saved payment token via this provider, instead of "
        "a bank payment order. Leave empty for bank-collected modes.",
    )
