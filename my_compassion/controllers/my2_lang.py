##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import route

from odoo.addons.website.controllers.main import Website

# Core sets "frontend_lang" as a session cookie, which the native app's WebView
# clears on a full close, so the chosen language reverts on reopen. Persist it
# for a year when the user explicitly picks a language.
FRONTEND_LANG_MAX_AGE = 365 * 24 * 60 * 60


class WebsiteLangPersist(Website):
    @route(
        "/website/lang/<lang>",
        type="http",
        auth="public",
        website=True,
        multilang=False,
    )
    def change_lang(self, lang, r="/", **kwargs):
        redirect = super().change_lang(lang, r=r, **kwargs)
        if hasattr(redirect, "set_cookie"):
            lang_code = redirect.get_cookie("frontend_lang")
            redirect.set_cookie(
                "frontend_lang", lang_code, max_age=FRONTEND_LANG_MAX_AGE
            )
        return redirect
