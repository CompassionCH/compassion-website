from odoo import models
from odoo.http import request

from odoo.addons.website.models.ir_http import ModelConverter


class SafeModelConverter(ModelConverter):
    """Model converter that builds its slug URL with sudo, so slugifying a
    record the public user cannot read does not raise AccessError."""

    def to_url(self, value):
        if hasattr(value, "sudo"):
            value = value.sudo()
        return super().to_url(value)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_converters(cls):
        return {**super()._get_converters(), "model_safe": SafeModelConverter}

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ["my_compassion"]

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()
        # Use default language if browser language is not supported
        lang = request.env.context.get("lang")
        if lang and not request.env["res.lang"]._get_data(code=lang):
            request.update_context(lang=request.website.default_lang_id.code)
