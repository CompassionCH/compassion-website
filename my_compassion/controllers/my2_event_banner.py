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
    """
    Normalizes the current page route by stripping query parameters and fragments.
    For example, "/dashboard?foo=bar#section" becomes "/dashboard".
    """
    if not route:
        return "/"
    route = route.split("?", 1)[0].split("#", 1)[0]
    return route


class MyCompassionEventBannerController(http.Controller):
    @http.route("/my2/active-event-banners", type="json", auth="public", website=True)
    def get_active_banner(self, current_page_route=None, limit=None, **kw) -> list:
        """
        Fetches active event banners based on the current page route and user
        partner tags.
        Parameters:
        - current_page_route: The route of the current page (e.g., "/dashboard").
        - limit: Optional limit on the number of banners to return.
        Returns a list of dictionaries containing banner IDs and their rendered HTML.
        """
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

        if request.env.user._is_public():
            user_tag_ids = []
        else:
            user_tag_ids = request.env.user.partner_id.sudo().category_id.ids

        now = fields.Datetime.now()
        domain = [
            # Only show banners that...
            # ... are active and have a start date in the past
            ("is_active", "=", True),
            ("start_date", "<=", now),
            "|",
            # ...have no end date or an end date in the future
            ("end_date", "=", False),
            ("end_date", ">=", now),
            "|",
            # ... have no route restrictions or match any of the possible routes
            ("target_route_ids", "=", False),
            ("target_route_ids.path", "in", possible_routes),
            "|",
            # ... have no partner tag restrictions or match any of the user's
            # partner tags
            ("target_partner_tag_ids", "=", False),
            ("target_partner_tag_ids", "in", user_tag_ids),
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

        # Render HTML for each banner and return it.
        # Returns an empty list if no banners found.
        return [
            {
                "id": banner.id,
                "html": request.env["ir.ui.view"]._render_template(
                    "theme_compassion_2025.EventBannerComponent", {"banner": banner}
                ),
            }
            for banner in (banners or [])
        ]
