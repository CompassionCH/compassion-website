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
        partner = None

        # Need sudo() to bypass domain restriction on res.partner for anonymous
        # users.
        if partner_uuid:
            partner = (
                request.env["res.partner"].sudo().search([("uuid", "=", partner_uuid)])
            )

        if not partner and not request.env.user._is_public():
            partner = request.env.user.partner_id
            partner_uuid = partner.uuid

        if not partner:
            return request.redirect("/")

        date_signed = partner.date_agreed_child_protection_charter
        if date_signed and (datetime.datetime.now() - date_signed).days < 365:
            return request.redirect("/partner/child-protection-charter-agreed")

        values = {
            "partner_uuid": partner_uuid,
            "redirect": kwargs.get("redirect"),
        }
        return request.render(
            "website_child_protection.child_protection_charter_page", values
        )

    @http.route(
        "/partner/child-protection-charter/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def child_protection_charter_submit(self, **kwargs):
        partner_uuid = kwargs.get("partner_uuid")
        agreed = kwargs.get("agreed")

        if not partner_uuid and not request.env.user._is_public():
            partner_uuid = request.env.user.partner_id.uuid

        if not agreed:
            return request.redirect(request.httprequest.referrer + "?error=required")

        partner = (
            request.env["res.partner"]
            .sudo()
            .search([("uuid", "=", partner_uuid)], limit=1)
        )

        if partner:
            partner.sudo().write(
                {"date_agreed_child_protection_charter": datetime.datetime.now()}
            )

            redirect_url = kwargs.get("redirect")
            target = "/partner/child-protection-charter-agreed"
            if redirect_url:
                target += "?redirect=" + redirect_url
            return request.redirect(target)

        return request.redirect("/")

    @http.route(
        route="/partner/child-protection-charter-agreed",
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_protection_charter_agreed(self, redirect=None, **kwargs):
        values = {
            "redirect": redirect or "/",
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
