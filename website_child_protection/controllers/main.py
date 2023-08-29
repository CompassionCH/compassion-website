##############################################################################
#
#    Copyright (C) 2019-2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Christopher Meier <dev@c-meier.ch>, Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import datetime

from odoo import http
from odoo.http import request


class ChildProtectionCharterController(http.Controller):
    """
    All the route controllers to agree to the child protection charter.
    """

    @http.route(
        route=[
            "/partner/<string:partner_uuid>/child-protection-charter",
            "/partner/child-protection-charter",
        ],
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_protection_charter(self, partner_uuid=None, **kwargs):
        """
        This page allows a partner to sign the child protection charter.
        :param partner_uuid: The uuid associated with the partner.
        :param kwargs: The remaining query string parameters.
        :return: The rendered web page.
        """
        # Need sudo() to bypass domain restriction on res.partner for anonymous
        # users.
        if partner_uuid:
            partner = (
                request.env["res.partner"].sudo().search([("uuid", "=", partner_uuid)])
            )
        else:
            partner = request.env.user.partner_id
            partner_uuid = partner.uuid

        if not partner:
            return request.redirect("/")

        current_time = datetime.datetime.now()
        date_signed = partner.date_agreed_child_protection_charter
        if date_signed and (current_time - date_signed).days < 365:
            return self.child_protection_charter_agreed(**kwargs)
        else:
            values = {"partner_uuid": partner_uuid}
            return request.render(
                "website_child_protection.child_protection_charter_page", values
            )

    @http.route(
        route="/partner/child-protection-charter-agreed",
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_protection_charter_agreed(self, redirect=None, **kwargs):
        values = {
            "redirect": redirect or request.httprequest.host_url,
        }
        return request.render(
            "website_child_protection.child_protection_charter_confirmation_page",
            values,
        )

    @http.route(
        route="/child-protection-charter",
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_protection_text_page(self, **kwargs):
        return request.render("website_child_protection.charter_only_page")
