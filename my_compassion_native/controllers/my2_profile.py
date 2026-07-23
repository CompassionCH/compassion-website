##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import http
from odoo.http import request


class My2MobileProfile(http.Controller):
    @http.route("/my2/user_profile", type="http", auth="user", website=True)
    def my2_user_profile(self, **kwargs):
        return request.render("my_compassion_native.my2_mobile_profile_page")
