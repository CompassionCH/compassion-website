from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    legal_agreement_date = fields.Datetime("Date of legal agreement", tracking=True)

    def anonymize(self, vals=None):
        self.with_context(tracking_disable=True).legal_agreement_date = False
        return super().anonymize(vals)
