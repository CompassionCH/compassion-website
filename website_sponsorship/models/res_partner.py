from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    legal_agreement_date = fields.Datetime("Date of legal agreement", tracking=True)
