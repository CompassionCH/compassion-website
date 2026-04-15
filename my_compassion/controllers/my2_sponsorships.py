##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import random
import uuid

from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import BadRequest, Gone, NotFound

from odoo import fields, http
from odoo.http import request

from odoo.addons.website_sponsorship.controllers.main import WebsiteChild
from odoo.addons.website_sponsorship.models.compassion_child import ChildNotFound

# Hold up to 3 children (more is too slow)
GLOBAL_FETCH_LIMIT = 3


class MyCompassionSponsorshipsController(WebsiteChild):
    @http.route(
        "/my2/sponsorships", type="http", auth="public", website=True, sitemap=False
    )
    def my2_render_sponsorships_page(self, **kwargs):
        """
        Renders the sponsorships landing page.
        return: An HTTP response containing a rendered template with the
        sponsorships landing page.
        """
        countries = request.env["compassion.field.office"].search(
            [
                ("available_on_childpool", "=", True),
                ("field_office_id", "!=", "ID"),  # Indonesia has two field offices
            ]
        )

        return request.render(
            "my_compassion.my2_sponsorships_page",
            {
                "countries": countries,
                "sponsorship_type": "standard",
            },
        )

    @http.route(
        "/my2/write-and-pray", type="http", auth="public", website=True, sitemap=False
    )
    def my2_render_write_and_pray_page(self, **kwargs):
        """
        Renders the write and pray variant of the sponsorships page.
        return: An HTTP response containing a rendered template with the
        sponsorships landing page.
        """
        countries = request.env["compassion.field.office"].search(
            [("available_on_childpool", "=", True)]
        )

        return request.render(
            "my_compassion.my2_sponsorships_page",
            {
                "countries": countries,
                "sponsorship_type": "write_and_pray",
            },
        )

    @http.route(
        "/my2/sponsorships/fetch",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def fetch_sponsorships(
        self, limit: int = 20, offset: int = 0, global_pool: bool = False, **post
    ):
        """
        Fetches children available for sponsorship and renders them using the
        my_compassion.my2_sponsorships_results_content template.
        return: An JSON response containing the rendered template html
        as well as the new children count and total hits.
        """
        child_obj = request.env["compassion.child"].sudo()
        if global_pool:
            try:
                post["limit"] = GLOBAL_FETCH_LIMIT
                child_obj.website_hold_child(post)
            except ChildNotFound:
                # Error is already logged, the frontend will just show no results
                pass
        # Query matching children
        domain = self._get_filtered_domain(post)
        total_results = child_obj.search_count(domain)
        children = child_obj.search(
            domain,
            limit=limit,
            offset=offset,
            order="unsponsored_since asc, create_date asc, completion_date asc",
        )

        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_sponsorships_results_content",
            {
                "children": children,
                "sponsorship_type": post.get("sponsorship_type", "standard"),
            },
        )

        return {
            "html": html_content,
            "count": len(children),
            "total": total_results,
        }

    @http.route(
        "/my2/sponsorships/fetch-random",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def fetch_random_child(self, **post):
        """
        Fetches a random child matching the search criteria.
        return: An JSON response containing the id of the random child.
        """
        # Get domain from filters
        domain = self._get_filtered_domain(post)

        # Query matching children
        child_obj = request.env["compassion.child"]
        total_results = child_obj.search_count(domain)

        child = None
        html_content = ""
        if total_results != 0:
            children = child_obj.search(
                domain,
                limit=1,
                offset=random.randint(0, total_results - 1),
            )

            if children:
                child = children[0]

                html_content = request.env["ir.qweb"]._render(
                    "my_compassion.my2_sponsorships_results_content",
                    {
                        "children": children,
                        "sponsorship_type": post.get("sponsorship_type", "standard"),
                    },
                )

        return {
            "child_id": child.id if child else None,
            "html": html_content,
        }

    @classmethod
    def _get_filtered_domain(cls, post):
        gender = post.get("gender", "either")
        age_min = int(post.get("age_min", 0))
        age_max = int(post.get("age_max", 18))
        country = post.get("country", "")

        child_obj = request.env["compassion.child"]

        # Filter by availability
        domain = [
            ("is_published", "=", True),
            ("state", "in", child_obj._available_states()),
            ("hold_id.expiration_date", ">", fields.Datetime.now()),
            ("hold_id.state", "=", "active"),
            "|",
            ("website_reservation_date", "=", False),
            "&",
            ("website_reservation_id", "=", request.session.session_token),
            ("website_reservation_id", "!=", False),
        ]

        # Filter by age
        domain += [
            ("age", ">=", age_min),
            ("age", "<=", age_max),
        ]

        # Filter by gender
        if gender != "either":
            domain += [("gender", "=", gender)]

        # Filter by country
        if country != "":
            domain += [("field_office_id.field_office_id", "=", country)]

        return domain


class MyCompassionNewSponsorshipController(http.Controller):
    @staticmethod
    def _extract_utm_information() -> dict:
        """
        Extracts utm medium, source and campaign information
        from the session and returns it.
        Return:
            a dictionary containing utm information or empty dict
        """
        utm_medium_str = request.session.get("wizard_utm_medium")
        utm_source_str = request.session.get("wizard_utm_source")
        utm_campaign_str = request.session.get("wizard_utm_campaign")

        if utm_medium_str or utm_source_str or utm_campaign_str:
            utm_vals = {}

            if utm_medium_str:
                medium = (
                    request.env["utm.medium"]
                    .sudo()
                    .search([("name", "=ilike", utm_medium_str)], limit=1)
                )
                if not medium:
                    medium = (
                        request.env["utm.medium"]
                        .sudo()
                        .create({"name": utm_medium_str})
                    )
                utm_vals["medium_id"] = medium.id

            if utm_source_str:
                source = (
                    request.env["utm.source"]
                    .sudo()
                    .search([("name", "=ilike", utm_source_str)], limit=1)
                )
                if not source:
                    source = (
                        request.env["utm.source"]
                        .sudo()
                        .create({"name": utm_source_str})
                    )
                utm_vals["source_id"] = source.id

            if utm_campaign_str:
                campaign = (
                    request.env["utm.campaign"]
                    .sudo()
                    .search([("name", "=ilike", utm_campaign_str)], limit=1)
                )
                if not campaign:
                    campaign = (
                        request.env["utm.campaign"]
                        .sudo()
                        .create({"name": utm_campaign_str})
                    )
                utm_vals["campaign_id"] = campaign.id

            # Clean up the session variables
            # so they don't bleed into future organic sessions
            request.session.pop("wizard_utm_medium", None)
            request.session.pop("wizard_utm_source", None)
            request.session.pop("wizard_utm_campaign", None)

            return utm_vals
        return {}

    @http.route(
        "/my2/new-sponsorship/<string:child_id>",
        type="http",
        auth="public",
        website=True,
    )
    def wizard_start(self, child_id, sponsorship_type="standard", **kwargs):
        """
        Renders the new sponsorship wizard initial page.
        return: An HTTP response containing a rendered template
        with the initial wizard page.
        """
        child = (
            request.env["compassion.child"]
            .sudo()
            .search([("id", "=", child_id)], limit=1)
        )

        if not child:
            raise NotFound("Child not found in database")

        # capture and store utm information
        utm_medium = kwargs.get("utm_medium")
        utm_source = kwargs.get("utm_source")
        utm_campaign = kwargs.get("utm_campaign")

        if utm_medium:
            request.session["wizard_utm_medium"] = utm_medium
        if utm_source:
            request.session["wizard_utm_source"] = utm_source
        if utm_campaign:
            request.session["wizard_utm_campaign"] = utm_campaign
        # Make sure child is available and reserve it for 5 minutes
        if child.state not in child._available_states():
            raise NotFound()
        reservation_uuid = self._get_reservation_uuid()
        if not child.sudo().reserve_for_web_sponsorship(reservation_uuid):
            raise Gone()

        # Create new wizard
        wizard = request.env["new.sponsorship.wizard"].create(
            {
                "child_id": child.id,
                "user_id": request.env.user.id,
                "sponsorship_type": sponsorship_type,
                "birthdate": request.env.user.birthdate_date
                if not request.env.user._is_public()
                else False,
            }
        )

        return request.render(
            "my_compassion.my2_new_sponsorship_wizard_page",
            {
                "form_content_html": self._render_form_content(wizard),
            },
        )

    @http.route(
        "/my2/new-sponsorship/step",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def wizard_step(self, **post):
        """
        Takes a step (forward or backward) in the new sponsorship wizard
        and renders the new wizard content using the
        my_compassion.my2_new_sponsorship_wizard_form_content template.
        return: An JSON response containing the rendered template html.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Update the record
        wizard.update(post)

        if wizard.is_done:
            return {"finish": True}
        else:
            return {"html": self._render_form_content(wizard)}

    @http.route(
        "/my2/new-sponsorship/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def sponsorship_wizard_submit(self, **post):
        """
        Receives the wizard form submission and finalizes the new sponsorship,
        then redirect to the thank-you page.
        return: A redirection to the thank-you page.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Cancel if person is too old for Write&Pray
        if (
            wizard.sponsorship_type == "write_and_pray"
            and wizard.birthdate
            < (fields.Datetime.now() - relativedelta(years=25)).date()
        ):
            raise BadRequest()

        # Make sure child is still available and finalize sponsorship creation
        if wizard.child_id.state not in wizard.child_id._available_states():
            raise Gone()
        sponsorship = wizard.finish_sponsorship()

        utm_values = self._extract_utm_information()
        if utm_values:
            sponsorship.sudo().write(utm_values)

        # Redirect to thank-you page
        return request.redirect(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )

    @http.route(
        "/my2/new-sponsorship/thank-you", type="http", auth="public", website=True
    )
    def wizard_thank_you(self, sponsorship_id, **kwargs):
        """
        Renders the new sponsorship thank-you page.
        return: An HTTP response containing a rendered template with the thank-you page.
        """
        sponsorship = (
            request.env["recurring.contract"].sudo().browse(int(sponsorship_id))
        )

        return request.render(
            "my_compassion.my2_new_sponsorship_thank_you_page",
            {
                "n_steps": 3,
                "sponsorship": sponsorship,
            },
        )

    @staticmethod
    def _render_form_content(wizard):
        # Fetch available salutations, countries, payment methods,
        # languages and lead sources
        titles = request.env["res.partner.title"].search([])
        countries = request.env["res.country"].search([])
        spoken_languages = (
            request.env["res.lang.compassion"]
            .sudo()
            .search([("translatable", "=", True)])
        )
        payment_methods = (
            request.env["account.payment.mode"]
            .sudo()
            .search([("website_published", "=", True)])
        )
        lead_sources = (
            request.env["recurring.contract.origin"]
            .sudo()
            .search(
                [
                    ("website_published", "=", True),
                ]
            )
        )
        currency_name = request.env.user.company_id.currency_id.name

        # Render step template first
        inner_step_html = request.env["ir.qweb"]._render(
            wizard.current_step.template,
            {
                "wizard": wizard,
                "titles": titles,
                "countries": countries,
                "payment_methods": payment_methods,
                "spoken_languages": spoken_languages,
                "lead_sources": lead_sources,
                "currency_name": currency_name,
            },
        )

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_new_sponsorship_wizard_form_content",
            {
                "wizard": wizard,
                "inner_step_html": inner_step_html,
                "currency_name": currency_name,
            },
        )

        return html_content

    @staticmethod
    def _get_reservation_uuid():
        reservation_uuid = request.session.get("reservation_uuid")
        if not reservation_uuid:
            if request.env.user._is_public():
                reservation_uuid = str(uuid.uuid4())
            else:
                reservation_uuid = request.env.user.partner_id.uuid
            request.session["reservation_uuid"] = reservation_uuid
        return reservation_uuid
