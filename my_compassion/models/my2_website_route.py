from odoo import models, fields, api
from odoo.http import request, root


class WebsiteRoute(models.Model):
    _name = "my_compassion.website_route"
    _description = "MyCompassion Website Route"
    _rec_name = "path"  # use the 'path' field as the display name for this model.
    _order = "path"

    path = fields.Char(string="Route Path", required=True, index=True)

    @api.model
    def action_refresh_routes_and_reload_view(self):
        """
        Updates the routes and return a success notification to the client
        """
        self._update_routes()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'The list of available website routes has been updated.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _get_my2_routes(self):
        """
        Scans the routes starting with '/my2/ and returns a set of paths.
        """
        paths = set()
        if not request or not getattr(request, "httprequest", None):
            return list(paths)

        router = root.get_db_router(self.env.cr.dbname)
        for rule in router.iter_rules():
            routing = getattr(rule.endpoint, "routing", {})
            if routing.get("website") and routing.get("type") == "http":
                if rule.rule.startswith("/my2/"):
                    paths.add(rule.rule)
        return sorted(list(paths))

    @api.model
    def _update_routes(self):
        """
        Synchronizes the routes in the database with the ones
        discovered from the controllers.
        """
        current_routes = self._get_my2_routes()
        existing_routes = self.search([]).mapped("path")

        new_routes = set(current_routes) - set(existing_routes)

        if new_routes:
            self.create([{"path": p} for p in new_routes])
