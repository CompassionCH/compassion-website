from odoo import models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    def get_current_website(self, fallback=True):
        # Check if the HTTP request exists and matches your path
        if request and request.httprequest.path.startswith("/my2"):
            # Find your specific website record
            target_website = self.env.ref("my_compassion.my2_website")
            if target_website:
                return target_website

        # Otherwise, fall back to Odoo's standard domain/session detection
        return super(Website, self).get_current_website(fallback=fallback)
