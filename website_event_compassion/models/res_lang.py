##############################################################################
#
#    Copyright (C) 2024 Compassion CH (http://www.compassion.ch)
#    @author: Clément Charmillot <ccharmillot@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class ResLang(models.Model):
    _inherit = "res.lang"

    def format(self, percent, value, grouping=False, monetary=False):
        res = super().format(percent, value, grouping, monetary)
        if self.code == "fr_CH":
            res = res.replace("'", "&nbsp;")
        return res
