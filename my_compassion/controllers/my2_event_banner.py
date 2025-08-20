# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller <ekeller@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json
from odoo import http
from odoo.http import request

class MyCompassionEventBannerController(http.Controller):

    @http.route('/my2/active-event-banners', type='json', auth='public', website=True)
    def get_active_banner(self, **kw):
        """
        This route is called by JavaScript to get the first active banner
        that should be displayed on the current page.
        """
        # TODO: add filters
        active_banners = request.env['my_compassion.event_banner'].search()

        if not active_banners:
            return {}

        current_path = request.httprequest.path
        for banner in active_banners:
            target_paths = [p.path.strip() for p in banner.target_page_ids if p.path]
            if current_path in target_paths:
                return {
                    'id': banner.id,
                    'text': banner.text,
                    'color': banner.color,
                    'pictogram': banner.pictogram,
                    'button_action': banner.button_action,
                }
        return {}
