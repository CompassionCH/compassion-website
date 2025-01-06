##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request
from odoo import http


class MyCompassionChildrenController(http.Controller):
    @http.route('/my2/children/', type="http", auth="public", website=True) # in public for testing purposes
    def my2_children(self, **kwargs):
        return request.render('my_compassion.my2_children')
