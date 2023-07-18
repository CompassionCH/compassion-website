##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models


class PrivacyStatementAgreement(models.Model):
    _inherit = ["compassion.privacy.statement", "website.published.multi.mixin"]
    _name = "compassion.privacy.statement"

    def _compute_website_url(self):
        for statement in self:
            statement.website_url = f"/data-protection/{statement.version}"
