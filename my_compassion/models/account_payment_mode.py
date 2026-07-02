from odoo import models


class PaymentMode(models.Model):
    _inherit = [
        "account.payment.mode",
        "website.published.mixin",
    ]
    _name = "account.payment.mode"
