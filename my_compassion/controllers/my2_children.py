##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

from werkzeug.exceptions import NotFound

from odoo import http

from odoo.http import request

class MyCompassionChildrenController(http.Controller):
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

        sponsorships_data = [] 

        # Iterate through each sponsorship of the partner
        for sponsorship in partner.sponsorship_ids:
            has_unread_letter = bool(
                request.env["correspondence"].search(
                    [
                        ("child_id", "=", sponsorship.child_id.id),
                        ("email_read", "=", False),
                        ("direction", "=", "Beneficiary To Supporter"),
                    ],
                    limit=1,
                )
            )

            # Calculate days until next birthday
            today = datetime.today().date()
            birthday_this_year = sponsorship.child_id.birthdate.replace(year=today.year)
            delta = (birthday_this_year - today).days
            # If the birthday has already occurred this year, calculate for next year
            if delta < 0:
                birthday_next_year = birthday_this_year.replace(year=today.year + 1)
                delta = (birthday_next_year - today).days

            # Calculate days since last letter
            last_letter = request.env["correspondence"].search(
                [
                    ("child_id", "=", sponsorship.child_id.id),
                    ("direction", "=", "Supporter To Beneficiary"),
                ],
                order="create_date DESC",
                limit=1,
            )

            if last_letter:
                last_letter_date = last_letter.create_date.date()
                delta_last_letter = (today - last_letter_date).days

        sponsorships_data.append(
            {
                "sponsorship": sponsorship,
                "has_unread_letter": has_unread_letter,
                "days_until_birthday": delta,
                "delta_last_letter": delta_last_letter if last_letter else None,
            }
        )

        return request.render(
            "my_compassion.my2_children_page",
            {
                "sponsorship_ids": partner.sponsorship_ids,
                "latest_correspondences_by_child_id": latest_corr_by_child,
                "breadcrumbs": breadcrumbs,
                "sponsorships_data": sponsorships_data,
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
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        if child in children_sponsored_by_partner:
            breadcrumbs = [
                {"name": "Children", "url": "/my2/children/", "active": False},
                {
                    "name": child.preferred_name,
                    "url": "/my2/children/" + str(child.id),
                    "active": True,
                },
            ]

            return request.render(
                "my_compassion.my2_child_timeline_page",
                {
                    "compassion_child": child,
                    "breadcrumbs": breadcrumbs,
                },
            )
        raise NotFound()

    @http.route(
        "/my2/children/<model("compassion.child"):child>/details", type="http", auth="user", website=True
    ,
        sitemap=False,
    )
    def my2_render_child_details_page(self, child, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        if child in children_sponsored_by_partner:
            breadcrumbs = [
                {"name": "Children", "url": "/my2/children/", "active": False},
                {
                    "name": child.preferred_name,
                    "url": "/my2/children/" + str(child.id),
                    "active": False,
                },
                {
                    "name": "Details",
                    "url": "/my2/children/" + str(child.id) + "/details",
                    "active": True,
                },
            ]

            return request.render(
                "my_compassion.my2_child_details_page",
                {
                    "compassion_child": child,
                    "breadcrumbs": breadcrumbs,
                },
            )
        raise NotFound()
