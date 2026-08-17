##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class Website(models.Model):
    _inherit = "website"

    def _get_safe_local_url(self, url):
        """Return url if it points to a location on this website, else ""."""
        url = url or ""
        is_local = (
            url.startswith("/")
            and not url.startswith("//")
            and "\\" not in url
            and not any(char.isspace() for char in url)
        )
        return url if is_local else ""
