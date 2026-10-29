##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class MyCompassionLegal(http.Controller):
    @http.route("/legal", type="http", auth="public", website=True, sitemap=False)
    def legal_redirect(self):
        """Privacy notice of the website (Privacy Policy URL, per language),
        the target of the "/legal" links of the MyCompassion pages."""
        legal_link = request.website.privacy_policy_url
        if legal_link:
            # local=False: an external URL, otherwise reduced to its path on
            # this website.
            return request.redirect(legal_link, code=302, local=False)
        # No URL for this website: its /legal page, if any (website_legal_page).
        page = request.env["ir.http"]._serve_page()
        if not page:
            raise NotFound()
        return page
