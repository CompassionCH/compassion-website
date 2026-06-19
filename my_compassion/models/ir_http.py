from odoo import models
from odoo.http import request

from odoo.addons.website.models.ir_http import ModelConverter

# Core sets "frontend_lang" as a session cookie, which the native app's WebView
# clears on a full close, so the chosen language reverts on reopen. Persist it
# for a year so the user's language choice survives.
FRONTEND_LANG_MAX_AGE = 365 * 24 * 60 * 60


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
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ["my_compassion"]

    @classmethod
    def _dispatch(cls):
        result = super()._dispatch()
        # Re-set the frontend language cookie with an expiry so it persists
        # across a full app close (core sets it as a session-only cookie).
        if request.is_frontend and request.lang and hasattr(result, "set_cookie"):
            result.set_cookie(
                "frontend_lang", request.lang.code, max_age=FRONTEND_LANG_MAX_AGE
            )
        return result
