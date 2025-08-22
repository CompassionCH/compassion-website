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

def _normalize_current_page_route(route: str) -> str:
    if not route:
        return '/'
    route = route.split('?', 1)[0].split('#', 1)[0]
    if route != '/' and route.endswith('/'):
        route = route[:-1]
    return route

class MyCompassionEventBannerController(http.Controller):

    @http.route('/my2/active-event-banners', type='json', auth='public', website=True)
    def get_active_banner(self, current_page_route=None,  limit=None,  **kw):

        current_page_route = _normalize_current_page_route(current_page_route)

        now = fields.Datetime.now()
        domain = [
            ('is_active', '=', True),
            ('start_date', '<=', now),
            '|', ('end_date', '=', False), ('end_date', '>=', now),
            '|', '|', '|',
            ('target_pages', '=', current_page_route),  # exakt (ein Eintrag)
            ('target_pages', 'ilike', f'{current_page_route};%'),  # am Anfang
            ('target_pages', 'ilike', f'%;{current_page_route};%'),  # in der Mitte
            ('target_pages', 'ilike', f'%;{current_page_route}'),
        ]

        banners = request.env['my_compassion.event_banner'].sudo().search(
            domain,
            order='start_date desc, id desc',
            limit=limit or None,
        )

        rendered_banners = []

        if not banners:
            return rendered_banners

        for banner in banners:
            values = {
                'id': banner.id,
                'title': banner.banner_title or '',
                'description': banner.banner_description or '',
                'start_date': banner.start_date,
                'end_date': banner.end_date,
                'is_active': banner.is_active,
                'pictogram': banner.pictogram or '',
                'pictogram_color': banner.pictogram_color ,

                'background_color': banner.background_color ,
                'button_color': banner.button_color ,
                'target_pages': banner.target_pages ,
                'button_action': banner.button_action,
            }
            html = request.env['ir.ui.view']._render_template(
                'theme_compassion_2025.EventBannerComponent', values
            )
            rendered_banners.append({'id': banner.id, 'html': html})
        return rendered_banners
