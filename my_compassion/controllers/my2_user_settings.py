##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nicolò Hepp <nhepp@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request
from odoo import http


class MyCompassionUserController(http.Controller):

    @http.route('/my2/user_settings', type="http", auth="user", website=True, sitemap=False)
    def my2_render_user_settings_page(self, **kwargs):


        return request.render(
            'my_compassion.my2_user_settings_page',
            {}
        )