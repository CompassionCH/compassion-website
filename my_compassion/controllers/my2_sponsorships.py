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
from datetime import datetime

from werkzeug.exceptions import Gone, NotFound

from odoo import fields, http
from odoo.http import request


class MyCompassionSponsorshipsController(http.Controller):
    @http.route(
        "/my2/sponsorships", type="http", auth="public", website=True, sitemap=False
    )
    def my2_render_sponsorships_page(self, **kwargs):
        """
        Renders the sponsorships landing page.
        return: An HTTP response containing a rendered template with the sponsorships landing page.
        """
        countries = request.env["compassion.field.office"].search(
            [("available_on_childpool", "=", True)]
        )

        return request.render(
            "my_compassion.my2_sponsorships_page",
            {
                "countries": countries,
            },
        )

    @http.route(
        "/my2/sponsorships/fetch",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def fetch_sponsorships(self, **post):
        """
        Fetches children available for sponsorship and renders them using the
        my_compassion.my2_sponsorships_results_content template.
        return: An JSON response containing the rendered template html as well as the new children count and total hits.
        """
        # The number of results to fetch per call
        limit = int(post.get("limit", 20))
        # The number of results to skip
        offset = int(post.get("offset", 0))

        # Get domain from filters
        domain = self._get_filtered_domain(post)

        # Query matching children
        child_obj = request.env["compassion.child"]
        total_results = child_obj.search_count(domain)
        children = child_obj.search(
            domain,
            limit=limit,
            offset=offset,
            order="unsponsored_since asc, create_date asc, completion_date asc",
        )

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_sponsorships_results_content", {"children": children}
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

        child_id = None
        if total_results != 0:
            children = child_obj.search(
                domain,
                limit=1,
                offset=random.randint(0, total_results - 1),
            )

            child_id = children[0].id if children else None

        return {
            "child_id": child_id,
        }

    def _get_filtered_domain(self, post):
        gender = post.get("gender", "either")
        min_age = int(post.get("min_age", 0))
        max_age = int(post.get("max_age", 18))
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
            ("age", ">=", min_age),
            ("age", "<=", max_age),
        ]

        # Filter by gender
        if gender != "either":
            domain += [("gender", "=", "F" if gender == "girl" else "M")]

        # Filter by country
        if country != "":
            domain += [("field_office_id", "=", int(country))]

        return domain


class MyCompassionNewSponsorshipController(http.Controller):
    @http.route(
        '/my2/new-sponsorship/<model("compassion.child"):child>',
        type="http",
        auth="public",
        website=True,
    )
    def wizard_start(self, child, **kwargs):
        """
        Renders the new sponsorship wizard initial page.
        return: An HTTP response containing a rendered template with the initial wizard page.
        """
        # Make sure child is available and reserve it for 5 minutes
        if child.state not in child._available_states():
            raise NotFound()
        reservation_uuid = self._get_reservation_uuid()
        if not child.sudo().reserve_for_web_sponsorship(reservation_uuid):
            raise Gone()

        # Create new wizard
        wizard = request.env["new.sponsorship.wizard"].create({})
        wizard.child = child

        # Fetch available salutations and countries
        titles = request.env["res.partner.title"].search([])
        countries = request.env["res.country"].search([])

        context = {
            "wizard": wizard,
            "titles": titles,
            "countries": countries,
        }

        return request.render("my_compassion.my2_new_sponsorship_wizard_page", context)

    @http.route(
        "/my2/new-sponsorship/step",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def wizard_step(self, **post):
        """
        Takes a step (forward or backward) in the new sponsorship wizard and renders the new wizard content using the
        my_compassion.my2_new_sponsorship_wizard_form_content template.
        return: An JSON response containing the rendered template html.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Update the record
        self._update_wizard(wizard, post)

        # Fetch available salutations, countries, payment methods, languages and lead sources
        titles = request.env["res.partner.title"].search([])
        countries = request.env["res.country"].search([])
        spoken_languages = (
            request.env["res.lang.compassion"]
            .sudo()
            .search([("translatable", "=", True)])
        )
        payment_methods = request.env["account.payment.mode"].sudo().search([])
        lead_sources = request.env["recurring.contract.origin"].sudo().search([])

        # TODO: decide if we filter by website_published or not
        # payment_methods = request.env["account.payment.mode"].sudo().search([("website_published", "=", True)])
        # lead_sources = request.env["recurring.contract.origin"].sudo().search([("website_published", "=", True)])

        context = {
            "wizard": wizard,
            "titles": titles,
            "countries": countries,
            "payment_methods": payment_methods,
            "spoken_languages": spoken_languages,
            "lead_sources": lead_sources,
        }

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_new_sponsorship_wizard_form_content", context
        )

        return {"html": html_content}

    @http.route(
        "/my2/new-sponsorship/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def sponsorship_wizard_submit(self, **post):
        """
        Receives the wizard form submission and finalizes the new sponsorship, then redirect to the thank you page.
        return: A redirection to the thank you page.
        """
        # Fetch the wizard record from the database
        wizard_id = int(post.get("wizard_id"))
        wizard = request.env["new.sponsorship.wizard"].sudo().browse(wizard_id)

        # Update wizard
        self._update_wizard(wizard, post)

        # Make sure child is still available and finalize sponsorship creation
        if wizard.child.state not in wizard.child._available_states():
            raise Gone()
        sponsorship = wizard.action_finish_sponsorship()

        # Redirect to thank-you page
        return request.redirect(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )

    @http.route(
        "/my2/new-sponsorship/thank-you", type="http", auth="public", website=True
    )
    def wizard_thank_you(self, sponsorship_id, **kwargs):
        """
        Renders the new sponsorship thank you page.
        return: An HTTP response containing a rendered template with the thank you page.
        """
        sponsorship = (
            request.env["recurring.contract"].sudo().browse(int(sponsorship_id))
        )

        return request.render(
            "my_compassion.my2_new_sponsorship_thank_you_page",
            {
                "n_steps": request.env["new.sponsorship.wizard"].n_steps,
                "sponsorship": sponsorship,
            },
        )

    @staticmethod
    def _update_wizard(wizard, post):
        values = {}

        def soft_convert(value, convert=lambda x: x):
            try:
                return convert(value)
            except (ValueError, TypeError):
                return None

        if wizard.step == 0:
            values["title"] = soft_convert(post.get("title"), int)
            values["lastname"] = post.get("lastname")
            values["firstname"] = post.get("firstname")
            values["birthdate"] = post.get("birthdate")
            values["email"] = post.get("email")
            values["phone"] = post.get("phone")
            values["street"] = post.get("street")
            values["street_number"] = post.get("street_number")
            values["zip"] = post.get("zip")
            values["city"] = post.get("city")
            values["country"] = post.get("country")

        if wizard.step == 1:
            values["payment_method"] = soft_convert(post.get("payment_method"), int)
            values["sponsorship_plus"] = soft_convert(
                post.get("sponsorship_plus"), bool
            )

        if wizard.step == 2:
            spoken_languages_ids = [
                int(post.get(key)) for key in post if key.startswith("spoken_language")
            ]
            values["spoken_languages"] = [(6, 0, spoken_languages_ids)]
            values["lead_source"] = soft_convert(post.get("lead_source"), int)
            values["volunteering"] = soft_convert(post.get("volunteering"), bool)

        wizard.write(values)

        # Move to previous / next step
        if "action" in post:
            action = post.get("action")
            if action == "next":
                wizard.action_next_step()
            elif action == "previous":
                wizard.action_previous_step()

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
