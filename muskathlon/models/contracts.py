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


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    sent_to_4m = fields.Date("Sent to 4M", copy=False)
