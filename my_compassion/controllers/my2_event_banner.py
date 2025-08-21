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
from odoo import http, fields
from odoo.http import request

class MyCompassionEventBannerController(http.Controller):

    @http.route('/my2/active-event-banners', type='json', auth='public', website=True)
    def get_active_banner(self, **kw):
        """
        This route is called by JavaScript to get the first active banner
        that should be displayed on the current page.
        """
        domain = [
            ('is_active', '=', True),
            ('start_date', '<=', fields.Datetime.now()),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', fields.Datetime.now())
        ]

        # 2. Suche nur nach den Bannern, die der Domain entsprechen.
        #    Dies ist viel performanter und speicherschonender.
        active_banners = request.env['my_compassion.event_banner'].search(domain)

        if not active_banners:
            return {}

        current_path = request.httprequest.path
        for banner in active_banners:
            #target_paths = [p.path.strip() for p in banner.target_page_ids if p.path]
            #if current_path in target_paths:
            return {
                'id': banner.id,
                'title': banner.banner_title,
                'description': banner.banner_description,
                'start_date': banner.start_date,
                'end_date': banner.end_date,
                'is_active': banner.is_active,
                'pictogram': banner.pictogram,
                'pictogram_color': banner.pictogram_color,
                'background_color': banner.background_color,
                'button_color': banner.button_color,
                'target_pages': banner.target_pages,
                'button_action': banner.button_action,
            }
        return {}
