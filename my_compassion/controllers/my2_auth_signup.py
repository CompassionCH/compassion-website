##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Zivi Service <zivi3@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from odoo.addons.auth_signup.controllers.main import AuthSignupHome

from .website_utils import resolve_host_my2_website


class SignupOverride(AuthSignupHome):
    @http.route("/web/signup", type="http", auth="public", website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """
        Overrides the original signup page controller.
        Redirects logged-in users.
        """

        if request.session.uid and resolve_host_my2_website():
            return request.redirect(kw.get("redirect") or "/my2/dashboard/")

        # If the user is not logged in, execute the original Odoo logic for signup
        return super().web_auth_signup(*args, **kw)
