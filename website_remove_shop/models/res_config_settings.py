from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shop_redirect_url = fields.Char(
        related="website_id.shop_redirect_url",
        readonly=False,
    )
