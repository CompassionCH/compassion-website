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

class WebsiteLoginRedirect(Website):

    @http.route('/web/login', type='http', auth="public", website=True, sitemap=False)
    def web_login(self, redirect="/web/login?redirect=/my2/children"):
        """
        Overrides the login page controller.
        If the user is already logged in, they are redirected immediately.
        """
        # Check if a user ID exists in the current session
        if request.session.uid:
            # If so, redirect the user to their account page or dashboard
            return request.redirect('/my2/dashboard/')

        # If the user is not logged in, execute the original Odoo logic
        return super(WebsiteLoginRedirect, self).web_login(redirect=redirect)
