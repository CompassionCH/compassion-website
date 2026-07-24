##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.addons.website.controllers.main import Website
from odoo.http import request

# Core sets "frontend_lang" as a session cookie, which the native app's WebView
# clears on a full close, so the chosen language reverts on reopen. Persist it
# for a year when the user explicitly picks a language.
FRONTEND_LANG_MAX_AGE = 365 * 24 * 60 * 60


class WebsiteLangPersist(Website):
    def change_lang(self, lang, r="/", **kwargs):
        redirect = super().change_lang(lang, r=r, **kwargs)
        # Persist the explicitly chosen language so it survives a full app
        # close. Re-derive the code the way core does, handling the default.
        if lang == "default":
            lang = request.website.default_lang_id.url_code
        lang_code = request.env["res.lang"]._get_data(url_code=lang).code or lang
        if hasattr(redirect, "set_cookie"):
            redirect.set_cookie(
                "frontend_lang", lang_code, max_age=FRONTEND_LANG_MAX_AGE
            )
        return redirect
