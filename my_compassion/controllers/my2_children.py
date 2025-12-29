##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json

import babel.dates

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.website_sponsorship.controllers.main import WebsiteChild


class MyCompassionChildrenController(WebsiteChild):
    def _get_formatted_birthday(self, child):
        """
        Formats the child's birthday based on the current language context.
        Handles specific rules for EN (US/UK), FR, IT, DE and nordic languages.
        """
        if not child.birthdate:
            return ""

        lang_code = request.env.lang
        birthdate = child.birthdate
        day = birthdate.day

        # Get localized month name
        month = babel.dates.format_date(birthdate, format="MMMM", locale=lang_code)

        # German, Norwegian, Danish, Finnish: Dot after day (e.g., 24. Januar)
        # Note: Swedish is excluded here as it typically uses a space (24 januari)
        if lang_code.startswith("de") or lang_code[:2] in [
            "no",
            "nb",
            "nn",
            "da",
            "fi",
        ]:
            return f"{day}. {month}"

        # Swedish, French, Italian: Space after day (e.g., 24 januari)
        if (
            lang_code.startswith("fr")
            or lang_code.startswith("it")
            or lang_code.startswith("sv")
        ):
            # French specific: 1st is "1er"
            if lang_code.startswith("fr") and day == 1:
                return f"1er {month}"
            return f"{day} {month}"

        # English Logic
        if lang_code.startswith("en"):
            # Suffix calculation
            # Special cases for 11, 12, 13.
            if 11 <= day <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

            # US Format: Month Day+Suffix
            if lang_code == "en_US":
                return f"{month} {day}{suffix}"

            # UK/Other English: Day+Suffix Month
            return f"{day}{suffix} {month}"

        # Fallback for other languages (Standard Day Month)
        return f"{day} {month}"

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

    def _get_authorized_partner_ids(self, child):
        """
        Get the list of partner IDs authorized to view timeline records.
        Includes the current partner and potentially the correspondent
        if portal settings allow.
        """
        partner = request.env.user.partner_id
        sponsorship = child.my_sponsorship_id

        # Include correspondent if user has full info access and isn't the correspondent
        if (
            partner != sponsorship.correspondent_id
            and partner.portal_sponsorships == "all_info"
        ):
            partner += sponsorship.correspondent_id

        return partner.ids

    def _get_timeline_count(self, child_id, partner_ids):
        """Get total count of timeline records (correspondence + gifts)."""
        sql = """
            SELECT
                (SELECT COUNT(*) FROM correspondence
                 WHERE child_id = %(child_id)s AND partner_id = ANY(%(partner_ids)s))
                +
                (SELECT COUNT(*) FROM sponsorship_gift
                 WHERE child_id = %(child_id)s AND partner_id = ANY(%(partner_ids)s))
                AS total
        """
        request.env.cr.execute(sql, {"child_id": child_id, "partner_ids": partner_ids})
        return request.env.cr.fetchone()[0] or 0

    def _get_timeline_data(self, child_id, partner_ids, offset, limit):
        """Fetch paginated timeline records (correspondence + gifts) ordered by date."""
        # ruff: noqa: E501 (query is more readable this way)
        sql = """
            SELECT * FROM (
                SELECT
                    'correspondence' AS model,
                    c.uuid::text AS record_id,
                    '' AS amount,
                    '' AS currency_name,
                    c.direction AS metadata,
                    c.create_date,
                    CASE
                        WHEN c.direction = 'Beneficiary To Supporter'
                        THEN %(title_corr_wrote)s
                        ELSE %(title_corr_received)s
                    END AS title
                FROM correspondence c
                WHERE c.child_id = %(child_id)s
                  AND c.partner_id = ANY(%(partner_ids)s)

                UNION ALL

                SELECT
                    'sponsorship_gift' AS model,
                    s.id::text AS record_id,
                    s.amount::text AS amount,
                    COALESCE(rc.name, %(default_currency)s) AS currency_name,
                    s.gift_type || '|' || COALESCE(s.sponsorship_gift_type, '') AS metadata,
                    s.create_date,
                    CASE
                        WHEN s.sponsorship_gift_type = 'Birthday' THEN %(title_gift_bday)s
                        WHEN s.sponsorship_gift_type = 'General' THEN %(title_gift_general)s
                        WHEN s.sponsorship_gift_type = 'Graduation/Final' THEN %(title_gift_grad)s
                        WHEN s.gift_type = 'Family Gift' THEN %(title_gift_family)s
                        ELSE %(title_gift_default)s
                    END AS title
                FROM sponsorship_gift s
                LEFT JOIN account_move_line aml ON aml.gift_id = s.id
                LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                WHERE s.child_id = %(child_id)s
                  AND s.partner_id = ANY(%(partner_ids)s)
            ) AS timeline
            ORDER BY create_date DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """

        params = {
            "child_id": child_id,
            "partner_ids": partner_ids,
            "default_currency": request.env.user.currency_id.name,
            "title_corr_wrote": _("Wrote you a letter"),
            "title_corr_received": _("Received your letter"),
            "title_gift_bday": _("Birthday gift"),
            "title_gift_general": _("General gift"),
            "title_gift_grad": _("Graduation/Final gift"),
            "title_gift_family": _("Family gift"),
            "title_gift_default": _("Received a gift"),
            "limit": limit,
            "offset": offset,
        }

        request.env.cr.execute(sql, params)
        return request.env.cr.dictfetchall()

    def _get_timeline_records(self, child_id, offset=0, limit=9):
        """
        Fetch timeline records (correspondence and gifts) for a child.

        :param child_id: ID of the child
        :param offset: Number of records to skip (for pagination)
        :param limit: Maximum number of records to return
        :return: Tuple of (records_list, total_count)
        """
        child = request.env["compassion.child"].browse(child_id)
        partner_ids = self._get_authorized_partner_ids(child)

        total = self._get_timeline_count(child_id, partner_ids)
        records = self._get_timeline_data(child_id, partner_ids, offset, limit)

        return records, total

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

        records, total = self._get_timeline_records(child.id, offset, limit)

        birthday_formatted = self._get_formatted_birthday(child)

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
                "birthday_formatted": birthday_formatted,
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

        records, total = self._get_timeline_records(child.id, offset, limit)
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
