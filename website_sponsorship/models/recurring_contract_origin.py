##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class RecurringContractOrigin(models.Model):
    # Makes it possible to publish origins in the sponsorship form
    _inherit = ["recurring.contract.origin", "website.published.mixin"]
    _name = "recurring.contract.origin"
