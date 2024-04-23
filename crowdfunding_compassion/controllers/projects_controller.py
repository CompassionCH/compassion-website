##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Quentin Gigon, Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from datetime import date, datetime

import werkzeug

from odoo.http import Controller, request, route

STEP_1_FIELDS = [
    "name",
    "description",
    "deadline",
    "presentation_video",
    "type",
    "facebook_url",
    "twitter_url",
    "instagram_url",
    "personal_web_page_url",
]
STEP_2_FIELDS = [
    "number_sponsorships_goal",
    "product_id",
    "product_description",
    "product_number_goal",
]
STEP_3_FIELDS = [
    "partner_id",
    "nickname",
    "personal_motivation",
    "sponsorship_card_audio",
    "sponsorship_card_file",
]


class ProjectsController(Controller):
    _project_post_per_page = 12

    @route(
        ["/projects", "/projects/page/<int:page>"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def get_projects_list(
        self, project_type=None, page=1, year=None, status="all", **opt
    ):
        if request.website:
            if (
                request.website
                == request.env.ref(
                    "crowdfunding_compassion.crowdfunding_website"
                ).sudo()
            ):
                domain = request.website.website_domain()
                filters = list(
                    filter(
                        None,
                        [
                            ("state", "!=", "draft"),
                            ("website_published", "=", True),
                            ("deadline", ">=", datetime(year, 1, 1)) if year else None,
                            ("deadline", "<=", datetime(year, 12, 31))
                            if year
                            else None,
                            ("type", "=", project_type) if project_type else None,
                            ("deadline", ">=", date.today())
                            if status == "active"
                            else None,
                            ("deadline", "<", date.today())
                            if status == "finish"
                            else None,
                        ],
                    )
                )
                filters += domain
                project_obj = request.env["crowdfunding.project"]
                total = project_obj.search_count(filters)

                pager = request.website.pager(
                    url="/projects",
                    total=total,
                    page=page,
                    step=self._project_post_per_page,
                    url_args={"type": project_type, "status": status},
                )

                projects = project_obj.sudo().get_active_projects(
                    offset=(page - 1) * self._project_post_per_page,
                    project_type=project_type,
                    domain=domain,
                    limit=self._project_post_per_page,
                    status=status,
                )
                return request.render(
                    "crowdfunding_compassion.project_list_page",
                    {
                        "projects": projects,
                        "status": status,
                        "type": project_type,
                        "pager": pager,
                    },
                )
            raise werkzeug.exceptions.BadRequest()

    @route(
        [
            "/projects/create",
            "/projects/create/page/<int:page>",
            "/projects/join/<int:project_id>",
        ],
        auth="public",
        type="http",
        method="POST",
        website=True,
        sitemap=False,
    )
    def project_creation(self, page=1, project_id=0, **kwargs):
        project = request.env["crowdfunding.project"]
        if project_id:
            project = project.browse(project_id)
            if not project.exists():
                raise werkzeug.exceptions.NotFound()
        if project_id and page == 1:
            # Joining project can skip directly to step2
            page = 2
        if page == 3 and not project_id:
            # Check if a project was set in session
            step2_id = request.session.get("project_creation_step2")
            if step2_id:
                project = (
                    request.env["cms.form.crowdfunding.project.step2"]
                    .browse(step2_id)
                    .project_id
                )
        values = {
            "page": page,
            "funds": request.env["product.product"]
            .sudo()
            .search([("activate_for_crowdfunding", "=", True)]),
            "project": project,
        }
        # Force saving session, otherwise we lose values between steps
        return request.render(
            "crowdfunding_compassion.project_creation_view_template",
            values,
            headers={"Cache-Control": "no-cache"},
        )
