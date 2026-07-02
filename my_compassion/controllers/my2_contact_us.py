from odoo import http
from odoo.http import request


class ContactUsPageController(http.Controller):
    @http.route("/contactus", type="http", auth="public", website=True, sitemap=True)
    def contactus(self, **kwargs):
        titles = (
            request.env["res.partner.title"]
            .sudo()
            .search([("is_shown_on_public_forms", "=", True)], order="shortcut asc")
        )
        return request.render("website.contactus", {"titles": titles})
