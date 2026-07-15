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

from odoo.addons.website.controllers.main import Website

from .website_utils import resolve_host_my2_website


class WebsiteLoginRedirect(Website):
    def _login_redirect(self, uid, redirect=None):
        """
        Override login redirection for MyCompassion.
        """
        if not redirect and resolve_host_my2_website():
            return "/my2/dashboard"
        return super()._login_redirect(uid, redirect=redirect)

    @http.route("/web/login", type="http", auth="public", website=True, sitemap=False)
    def web_login(self, *args, **kw):
        """
        Overrides the login page controller for MyCompassion.
        An already authenticated visitor on MyCompassion is sent
        to the dashboard.
        """
        if (
            request.session.uid
            and not kw.get("redirect")
            and resolve_host_my2_website()
        ):
            return request.redirect("/my2/dashboard")

        return super().web_login(*args, **kw)
