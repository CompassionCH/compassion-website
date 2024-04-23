from odoo import api, models


class ResPartnerMatch(models.AbstractModel):
    _inherit = "res.partner.match"

    @api.model
    def _get_valid_create_fields(self):
        res = super()._get_valid_create_fields()
        res.append("image_1920")
        return res

    @api.model
    def _get_valid_update_fields(self):
        res = super()._get_valid_update_fields()
        res.append("image_1920")
        return res

    @api.model
    def _preprocess_vals(self, vals):
        """Transform, if needed and before matching, the infos received"""
        super()._preprocess_vals(vals)
        for key in vals.keys():
            if key.startswith("image_"):
                vals[key] = vals[key].decode("utf-8")
