from odoo import models


class ResPartnerTitle(models.Model):
    _inherit = ["res.partner.title", "website.published.mixin"]
    _name = "res.partner.title"
