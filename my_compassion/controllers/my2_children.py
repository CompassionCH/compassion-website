##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.website_sponsorship.controllers.main import WebsiteChild


class MyCompassionChildrenController(WebsiteChild):
    def _check_sponsored_child_access(self, child):
        """
        Private helper to securely fetch a sponsored child.
        Ensures the current user is a sponsor of the requested child.
        :param child: The requested child record to fetch.
        :raises: odoo.exceptions.AccessError if the user is not an active sponsor.
        """
        if child.state == "N":
            reservation_uuid = self._get_reservation_uuid()
            if (
                not child.website_published
                or not child.is_available_for_web_sponsorship(reservation_uuid)
            ):
                raise AccessError(_("This child is not available for sponsorship."))
        if child.state == "P":
            if (
                not request.env.user.partner_id.sponsorship_ids.mapped("child_id")
                & child
            ):
                raise AccessError(
                    _("You are not authorized to view this child's information.")
                )

    def _get_timeline_records(self, partner_id, child_id, offset=0, limit=9):
        sql_count = """
            SELECT SUM(c) FROM (
                (SELECT COUNT(*) as c FROM correspondence WHERE child_id = %s AND partner_id = %s)
                UNION ALL
                (SELECT COUNT(*) as c FROM sponsorship_gift WHERE child_id = %s AND partner_id = %s)
            ) AS counts
        """
        request.env.cr.execute(sql_count, (child_id, partner_id, child_id, partner_id))
        total = request.env.cr.fetchone()[0] or 0
        title_corr_wrote = _("Wrote you a letter")
        title_corr_received = _("Received your letter")
        title_gift_bday = _("Birthday gift")
        title_gift_general = _("General gift")
        title_gift_grad = _("Graduation/Final gift")
        title_gift_family = _("Family gift")
        title_gift_default = _("A gift")
        sql_data = """
            (SELECT
                'correspondence' AS model,
                c.uuid::text AS record_id,
                '' AS amount,
                '' AS currency_name,
                c.direction AS metadata,
                c.create_date,
                CASE WHEN c.direction = 'Beneficiary To Supporter' THEN %s ELSE %s END AS title
             FROM correspondence c
             WHERE c.child_id = %s AND c.partner_id = %s)
            UNION ALL
            (SELECT
                'sponsorship_gift' AS model,
                s.id::text AS record_id,
                s.amount::text AS amount,
                COALESCE(rc.name, 'CHF') AS currency_name,
                s.gift_type || '|' || COALESCE(s.sponsorship_gift_type, '') AS metadata,
                s.create_date,
                CASE
                    WHEN s.gift_type = 'Birthday' THEN %s
                    WHEN s.gift_type = 'General' THEN %s
                    WHEN s.gift_type = 'Graduation/Final' THEN %s
                    WHEN s.gift_type = 'Family Gift' THEN %s
                    ELSE %s
                END AS title
             FROM sponsorship_gift s
             LEFT JOIN account_move_line aml ON aml.gift_id = s.id
             LEFT JOIN res_currency rc ON rc.id = aml.currency_id
             WHERE s.child_id = %s AND s.partner_id = %s)
            ORDER BY create_date DESC
            LIMIT %s OFFSET %s
        """
        params = (
            title_corr_wrote,
            title_corr_received,
            child_id,
            partner_id,
            title_gift_bday,
            title_gift_general,
            title_gift_grad,
            title_gift_family,
            title_gift_default,
            child_id,
            partner_id,
            limit,
            offset,
        )
        request.env.cr.execute(sql_data, params)
        records_data = request.env.cr.dictfetchall()

        return records_data, total

    @http.route("/my2/children", type="http", auth="user", website=True, sitemap=False)
    def my2_render_children_page(self, **kwargs):
        """
        Renders the children page related to the logged-in user's sponsorships.
        return: An HTTP response containing a rendered template with sponsorship data.
        """
        partner = request.env.user.partner_id

        # To keep a list of the latest correspondence with each sponsored child:
        latest_corr_by_child = {}
        correspondences_table = request.env["correspondence"].sudo()

        received_correspondences = correspondences_table.search(
            [
                ("partner_id", "=", partner.id),
                ("direction", "=", "Beneficiary To Supporter"),
            ],
            order="create_date desc",
        )

        for corr in received_correspondences:
            child_id = corr.child_id.id
            if child_id not in latest_corr_by_child:
                latest_corr_by_child[child_id] = corr

        breadcrumbs = [
            {"name": "Children", "url": "/my2/children/", "active": True},
        ]
        sponsorships = partner.sponsorship_ids.filtered("can_show_on_my_compassion")

        return request.render(
            "my_compassion.my2_children_page",
            {
                "active_sponsorships": sponsorships.filtered(
                    lambda s: s.state != "terminated" or s.sds_state == "sub_waiting"
                ),
                "ended_sponsorships": sponsorships.filtered(
                    lambda s: s.state == "terminated" and s.sds_state != "sub_waiting"
                ),
                "latest_correspondences_by_child_id": latest_corr_by_child,
                "breadcrumbs": breadcrumbs,
            },
        )

    @http.route(
        '/my2/children/<model("compassion.child"):child>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_render_child_timeline_page(self, child, **kwargs):
        """Renders the main timeline page with the initial batch of records."""
        try:
            self._check_sponsored_child_access(child)
        except AccessError:
            return request.redirect("/my2/children/")

        access_scope = "public" if child.is_published else "sponsor"

        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 9))
        partner = request.env.user.partner_id

        records, total = self._get_timeline_records(partner.id, child.id, offset, limit)

        google_api_key = (
            request.env["ir.config_parameter"].sudo().get_param("google_maps_api_key")
        )
        google_custom_map_id = (
            request.env["ir.config_parameter"].sudo().get_param("google_custom_map_id")
        )

        return request.render(
            "my_compassion.my2_child_timeline_page",
            {
                "compassion_child": child.sudo(),
                "records": records,
                "has_more_records": total > offset + limit,
                "access_scope": access_scope,
                "google_api_key": google_api_key,
                "google_custom_map_id": google_custom_map_id,
                "timezone": child.sudo().project_id.timezone,
            },
        )

    @http.route(
        '/my2/children/<model("compassion.child"):child>/timeline-batch',
        type="json",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_get_child_timeline_items(self, child, **kwargs):
        """API endpoint for infinite scroll. Returns a rendered HTML snippet."""
        try:
            self._check_sponsored_child_access(child)
        except AccessError:
            # For an API, it's better to return an empty or error response
            # than to redirect.
            return request.make_response("", headers={"Content-Type": "text/html"})

        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 9))

        partner = request.env.user.partner_id

        records, total = self._get_timeline_records(partner.id, child.id, offset, limit)
        has_more = total > offset + limit

        html = (
            request.env["ir.ui.view"]._render_template(
                "my_compassion.SponsorChildTimelineBatchComponent",
                {
                    "records": records,
                    "has_more_records": has_more,
                },
            )
            if records
            else ""
        )

        return {
            "html": html,
            "has_more_records": has_more,
        }

    @http.route(
        '/my2/children/<model("compassion.child"):child>/center-weather',
        type="http",
        auth="user",
        website=True,
    )
    def get_center_weather(self, child, **kw):
        """
        This controller returns the child's center weather as a JSON object.
        """

        try:
            self._check_sponsored_child_access(child)
        except AccessError:
            return request.make_response(
                json.dumps({"error": "Access Denied"}),
                headers=[("Content-Type", "application/json")],
                status=403,
            )
        project = child.sudo().project_id
        center_temperature = project.current_temperature_celsius
        weather_icon_id = project.weather_icon_id
        data = {
            "current_temperature": center_temperature,
            "weather_icon_id": weather_icon_id,
        }

        return request.make_response(
            json.dumps(data), headers=[("Content-Type", "application/json")]
        )
