##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# -*- coding: utf-8 -*-
from odoo import http
from odoo.tools.translate import _

from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class WebsitePasswordReset(AuthSignupHome):
    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        """
        Adds an 'additional_title' to the password reset page.
        """
        response = super().web_auth_reset_password(*args, **kw)

        # Inject page title
        if hasattr(response, 'qcontext'):
            response.qcontext['additional_title'] = _('Reset Password')

        return response