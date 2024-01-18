##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#    @author: Sebastien Toth <popod@me.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    sent_to_4m = fields.Date("Sent to 4M", copy=False)
    price_cents = fields.Float(compute="_compute_amount_cents")

    def _compute_amount_cents(self):
        for line in self:
            line.price_cents = line.price_subtotal * 100
