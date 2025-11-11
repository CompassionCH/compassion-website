##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Samuel Bachmann <samuel.bachmann02@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import Website

class WebsiteHomeRedirect(Website):
    @http.route("/", type="http", auth="public", website=True, sitemap=False)
    def home(self, *args, **kw):
        """
        Redirects the home page.
        If the user is already logged in, they are redirected to the dashboard.
        If the user is not logged in, they are redirected to the login page.
        `my2_login.py` handles the redirection from the login page to the dashboard.
        """
        if request.session.uid:
            return request.redirect('/my2/dashboard/')
        return request.redirect('/web/login')
