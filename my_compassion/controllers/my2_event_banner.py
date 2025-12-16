##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller <ekeller@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, http
from odoo.http import request


def _normalize_current_page_route(route: str) -> str:
    if not route:
        return "/"
    route = route.split("?", 1)[0].split("#", 1)[0]
    return route


class MyCompassionEventBannerController(http.Controller):
    @http.route("/my2/active-event-banners", type="json", auth="public", website=True)
    def get_active_banner(self, current_page_route=None, limit=None, **kw):
        current_page_route = _normalize_current_page_route(current_page_route)

        # Get all active language codes to check for URL prefixes
        lang_codes = [
            lang[0] for lang in request.env["res.lang"].sudo().get_installed()
        ]
        path_parts = current_page_route.split("/")
        possible_routes = [current_page_route]

        # If the path starts with a language code (e.g., /fr/dashboard),
        # also search for the path without the language prefix.
        if len(path_parts) > 1 and path_parts[1] in lang_codes:
            unprefixed_route = "/" + "/".join(path_parts[2:])
            possible_routes.append(unprefixed_route)

        now = fields.Datetime.now()
        domain = [
            ("is_active", "=", True),
            ("start_date", "<=", now),
            "|",
            ("end_date", "=", False),
            ("end_date", ">=", now),
            # Match either the full path or the path without the lang prefix
            ("target_route_ids.path", "in", possible_routes),
        ]

        banners = (
            request.env["event.banner"]
            .sudo()
            .search(
                domain,
                order="start_date desc, id desc",
                limit=limit or None,
            )
        )

        rendered_banners = []

        if not banners:
            return rendered_banners

        for banner in banners:
            html = request.env["ir.ui.view"]._render_template(
                "theme_compassion_2025.EventBannerComponent", {"banner": banner}
            )
            rendered_banners.append({"id": banner.id, "html": html})
        return rendered_banners
