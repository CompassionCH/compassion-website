##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class MyCompassionChildrenController(http.Controller):
    def _get_sponsored_child_and_check_access(self, child_id):
        """
        Private helper to securely fetch a sponsored child.
        Ensures the current user is a sponsor of the requested child.
        :param child_id: The ID of the child to fetch.
        :return: A recordset of the 'compassion.child'.
        :raises: odoo.exceptions.AccessError if the user is not an active sponsor.
        """
        partner = request.env.user.partner_id
        child = partner.sponsorship_ids.filtered(
            lambda s: s.child_id.id == child_id
        ).mapped("child_id")
        if not child:
            raise AccessError(
                "You are not authorized to view this child's information."
            )
        return child

    def _get_timeline_records(self, partner_id, child_id, offset=0, limit=9):
        """Private helper to fetch a paginated list of timeline records."""
        domain = [("child_id", "=", child_id), ("partner_id", "=", partner_id)]
        timeline_model = request.env["compassion.sponsor_child_timeline"].sudo()
        total = timeline_model.search_count(domain)
        records = timeline_model.search(
            domain, order="create_date desc", offset=offset, limit=limit
        )
        return records, total

    @http.route("/my2/children/", type="http", auth="user", website=True, sitemap=False)
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

        return request.render(
            "my_compassion.my2_children_page",
            {
                "sponsorship_ids": partner.sponsorship_ids,
                "latest_correspondences_by_child_id": latest_corr_by_child,
                "breadcrumbs": breadcrumbs,
            },
        )

    @http.route(
        '/my2/children/<model("compassion.child"):child>',
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_child_timeline_page(self, child, **kwargs):
        """Renders the main timeline page with the initial batch of records."""
        try:
            child = self._get_sponsored_child_and_check_access(child.id)
        except AccessError:
            return request.redirect("/my2/children/")

        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 9))
        partner = request.env.user.partner_id

        records, total = self._get_timeline_records(partner.id, child.id, offset, limit)

        return request.render(
            "my_compassion.my2_child_timeline_page",
            {
                "compassion_child": child,
                "breadcrumbs": [
                    {"name": "Children", "url": "/my2/children/", "active": False},
                    {
                        "name": child.preferred_name,
                        "url": f"/my2/children/" + str(child.id),
                        "active": True,
                    },
                ],
                "records": records,
                "has_more_records": total > offset + limit,
            },
        )

    @http.route(
        "/my2/children/<int:child_id>/timeline-batch",
        type="json",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_get_child_timeline_items(self, child_id, **kwargs):
        """API endpoint for infinite scroll. Returns a rendered HTML snippet."""
        try:
            child = self._get_sponsored_child_and_check_access(child_id)
        except AccessError:
            # For an API, it's better to return an empty or error response than to redirect.
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
