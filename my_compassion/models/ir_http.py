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
        if request.is_frontend and hasattr(result, "set_cookie"):
            # A language switch (/website/lang/<lang>) already set frontend_lang
            # on this response; keep that value (request.lang is still the old
            # language here) so switching back to the prefix-less default
            # language is not clobbered. Otherwise persist the current one.
            lang_code = cls._pending_frontend_lang(result)
            if not lang_code and getattr(request, "lang", False):
                lang_code = request.lang.code
            if lang_code:
                result.set_cookie(
                    "frontend_lang", lang_code, max_age=FRONTEND_LANG_MAX_AGE
                )
        return result

    @staticmethod
    def _pending_frontend_lang(result):
        for header in result.headers.getlist("Set-Cookie"):
            if header.startswith("frontend_lang="):
                return header.split("=", 1)[1].split(";", 1)[0]
        return None
