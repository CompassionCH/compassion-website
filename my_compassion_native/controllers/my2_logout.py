##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.session import Session


class MyCompassionLogout(Session):
    @http.route("/web/session/logout", type="http", auth="none")
    def logout(self, redirect="/web", **kw):
        # Grab the token from this specific device's session BEFORE Odoo destroys it
        fcm_token = request.session.get("mycompassion_device_token")

        # If it exists, delete it from the database
        if fcm_token:
            TokenModel = request.env["mycompassion.device.token"].sudo()
            existing_tokens = TokenModel.search([("token", "=", fcm_token)])
            if existing_tokens:
                existing_tokens.unlink()

        parsed = urlparse(redirect)
        safe_redirect = (
            redirect if (not parsed.scheme and not parsed.netloc) else "/web"
        )
        return super().logout(redirect=safe_redirect)
