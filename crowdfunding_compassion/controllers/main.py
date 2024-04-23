##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Quentin Gigon
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request, route

from odoo.addons.website_event_compassion.controllers.events_controller import (
    EventsController,
)


class CrowdFundingWebsite(EventsController):
    @route(["/my/together"], type="http", auth="user", website=True, sitemap=False)
    def my_account(self, form_id=None, **kw):
        """Inject data for forms."""
        values = {}
        partner = request.env.user.partner_id
        participations = request.env["crowdfunding.participant"].search(
            [
                ("partner_id", "=", partner.id),
                ("project_id.project_owner_id", "!=", partner.id),
            ]
        )
        donations = (
            request.env["account.move.line"]
            .sudo()
            .search(
                [
                    ("crowdfunding_participant_id.partner_id", "=", partner.id),
                    ("payment_state", "=", "paid"),
                ]
            )
        )

        owned_projects = request.env["crowdfunding.project"].search(
            [("project_owner_id", "=", partner.id)]
        )

        values.update(
            {
                "partner": partner,
                "owned_projects": owned_projects,
                "participating_projects": participations,
                "donations": donations,
            }
        )

        result = request.render(
            "crowdfunding_compassion.my_account_crowdfunding_view_template", values
        )
        return result

    @route(
        ["/my/together/project/<model('crowdfunding.project'):project>/"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_account_projects_update(self, project, **kw):
        values = {
            "project": project,
        }
        return request.render("crowdfunding_compassion.edit_project_form", values)

    @route(
        ["/my/together/participant/<model('crowdfunding.participant'):participant>/"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_account_participants_update(self, participant, **kw):
        values = {
            "participant": participant,
        }
        return request.render("crowdfunding_compassion.edit_participation_form", values)
