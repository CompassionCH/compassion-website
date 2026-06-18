from odoo import models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    def get_current_website(self, fallback=True):
        if request:
            path = request.httprequest.path
            # Check if path starts with /my2 or a localized version like
            # /de/my2, /fr/my2, etc.
            # Splitting by '/' and checking the first/second segment is safest
            path_parts = [p for p in path.split("/") if p]

            is_my2_route = False
            if path_parts:
                # Direct check: /my2...
                if path_parts[0] == "my2":
                    is_my2_route = True
                # Localized check: /de/my2... or /fr/my2...
                elif len(path_parts) > 1 and path_parts[1] == "my2":
                    is_my2_route = True

            if is_my2_route:
                target_website = self.env.ref("my_compassion.my2_website")
                if target_website:
                    return target_website

        return super(Website, self).get_current_website(fallback=fallback)
