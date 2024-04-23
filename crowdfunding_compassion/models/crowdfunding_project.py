#    Copyright (C) 2020 Compassion CH
#    @author: Quentin Gigon
import base64
import urllib.parse as urlparse
from datetime import date, datetime

from babel.dates import format_timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import ImageProcess, file_open, ormcache

from ..exceptions import InvalidDeadlineException


class CrowdfundingProject(models.Model):
    _name = "crowdfunding.project"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
        "mail.thread",
        "mail.activity.mixin",
        "website.multi.mixin",
    ]
    _inherits = {"utm.campaign": "campaign_id"}
    _description = "Crowd-funding project"

    website_id = fields.Many2one(
        "website",
        default=lambda s: s.env.ref("crowdfunding_compassion.crowdfunding_website").id,
    )
    description = fields.Text(
        "Project description",
        help="Aim of the project, why you want to create it, for which purpose and "
        "any useful information that the donors should know.",
        required=True,
        translate=True,
    )
    description_short = fields.Text(compute="_compute_description_short")
    type = fields.Selection(
        [("individual", "Individual"), ("collective", "Collective")],
        required=True,
        default="individual",
        index=True,
    )
    deadline = fields.Date(
        "Deadline of project",
        help="Indicate when your project should end.",
        required=True,
        index=True,
    )
    time_left = fields.Char(compute="_compute_time_left")
    cover_photo = fields.Image(
        "Cover Photo",
        help="Upload a cover photo that represents your project. Best size: 900x400px",
        required=False,
        max_width=1024,
        max_height=512,
    )
    cover_photo_url = fields.Char(compute="_compute_cover_photo_url", required=False)
    presentation_video = fields.Char(
        help="Paste any video link that showcase your project"
        " (e.g. https://vimeo.com/jlkj34ek5)"
    )
    presentation_video_embed = fields.Char(compute="_compute_presentation_video_embed")
    facebook_url = fields.Char("Facebook link")
    twitter_url = fields.Char("Twitter link")
    instagram_url = fields.Char("Instagram link")
    personal_web_page_url = fields.Char("Personal web page")
    product_id = fields.Many2one(
        "product.product",
        "Supported fund",
        domain=[("activate_for_crowdfunding", "=", True)],
    )
    product_number_goal = fields.Integer(
        "Product goal", compute="_compute_product_number_goal"
    )
    product_number_reached = fields.Integer(
        "Product reached", compute="_compute_product_number_reached"
    )
    amount_reached = fields.Integer(compute="_compute_product_number_reached")
    number_sponsorships_goal = fields.Integer(
        "Sponsorships goal", compute="_compute_number_sponsorships_goal"
    )
    number_sponsorships_reached = fields.Integer(
        "Sponsorships reached", compute="_compute_number_sponsorships_reached"
    )
    number_csp_goal = fields.Integer(
        "Sponsorships goal", compute="_compute_number_sponsorships_goal"
    )
    number_csp_reached = fields.Integer(
        "Sponsorships reached", compute="_compute_number_sponsorships_reached"
    )
    product_crowdfunding_impact = fields.Char(compute="_compute_impact_text")
    color_sponsorship = fields.Char(compute="_compute_color_sponsorship")
    color_product = fields.Char(compute="_compute_color_product")
    color = fields.Integer(
        compute="_compute_color", inverse="_inverse_color", store=True
    )
    sponsorship_ids = fields.Many2many(
        "recurring.contract", string="Sponsorships", compute="_compute_sponsorships"
    )
    csp_sponsorship_ids = fields.Many2many(
        "recurring.contract", string="Sponsorships", compute="_compute_csp_sponsorships"
    )
    invoice_line_ids = fields.One2many(
        "account.move.line", compute="_compute_invoice_line_ids", string="Donations"
    )
    project_owner_id = fields.Many2one("res.partner", "Project owner", required=True)
    owner_participant_id = fields.Many2one(
        "crowdfunding.participant", compute="_compute_owner_participant_id"
    )
    participant_ids = fields.One2many(
        "crowdfunding.participant", "project_id", string="Participants", required=True
    )
    number_participants = fields.Integer(compute="_compute_number_participants")
    event_id = fields.Many2one("crm.event.compassion", "Event")
    campaign_id = fields.Many2one(
        "utm.campaign", "UTM Campaign", required=True, ondelete="cascade"
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("done", "Done")],
        required=True,
        default="draft",
        readonly=True,
    )
    owner_lastname = fields.Char(string="Your lastname")
    owner_firstname = fields.Char(string="Your firstname")
    active = fields.Boolean(default=True)

    @api.constrains("deadline", "state")
    def _check_deadline(self):
        for project in self:
            if project.state != "done" and project.deadline < date.today():
                raise InvalidDeadlineException

    @api.constrains("type", "participant_ids")
    def _check_type(self):
        for project in self:
            if project.type == "individual" and len(project.participant_ids) > 1:
                raise ValidationError(
                    _("Individual project can only have one participant.")
                )

    def _compute_description_short(self):
        for project in self:
            if len(project.description) > 100:
                project.description_short = project.description[0:100] + "..."
            else:
                project.description_short = project.description

    @api.depends("is_published")
    def _compute_color(self):
        for project in self:
            if project.website_published:
                project.color = 10
            else:
                project.color = 1

    def _inverse_color(self):
        # Allow setting manually a color
        return True

    def _compute_color_sponsorship(self):
        for project in self:
            if project.number_sponsorships_goal != 0:
                tx_sponsorships = (
                    project.number_sponsorships_reached
                    / project.number_sponsorships_goal
                ) * 100
                if tx_sponsorships >= 75.0:
                    project.color_sponsorship = "badge badge-success"
                else:
                    if 50.0 <= tx_sponsorships < 75.0:
                        project.color_sponsorship = "badge badge-warning"
                    else:
                        project.color_sponsorship = "badge badge-danger"
            else:
                project.color_sponsorship = "badge badge-info"

    def _compute_color_product(self):
        for project in self:
            if project.product_number_goal != 0:
                tx_product = (
                    project.product_number_reached / project.product_number_goal
                ) * 100
                if tx_product >= 75.0:
                    project.color_product = "badge badge-success"
                else:
                    if 50.0 <= tx_product < 75.0:
                        project.color_product = "badge badge-warning"
                    else:
                        project.color_product = "badge badge-danger"
            else:
                project.color_product = "badge badge-info"

    def _compute_number_participants(self):
        for project in self:
            project.number_participants = len(project.participant_ids)

    def _compute_impact_text(self):
        for project in self:
            product = project.product_id
            project.product_crowdfunding_impact = (
                product.crowdfunding_impact_text_passive_singular
                if product.impact_type == "large"
                else product.crowdfunding_impact_text_passive_plural
            )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        event = self.env["crm.event.compassion"].create(
            {
                "name": vals.get("name"),
                "type": "crowdfunding",
                "crowdfunding_project_id": res.id,
                "company_id": self.env.user.company_id.id,
                "start_date": vals.get("deadline"),
                "end_date": vals.get("deadline"),
                "hold_start_date": date.today(),
                "number_allocate_children": vals.get("product_number_goal"),
                "planned_sponsorships": vals.get("number_sponsorships_goal"),
                "ambassador_config_id": self.env.ref(
                    "crowdfunding_compassion.config_donation_received"
                ).id,
            }
        )
        res.event_id = event
        self.env["recurring.contract.origin"].create(
            {
                "type": "crowdfunding",
                "event_id": event.id,
                "analytic_id": event.analytic_id.id,
            }
        )
        res.add_owner2participants()
        return res

    def add_owner2participants(self):
        """Add the project owner to the participant list."""
        for project in self:
            if project.project_owner_id not in project.participant_ids.mapped(
                "partner_id"
            ):
                participant = {
                    "partner_id": project.project_owner_id.id,
                    "project_id": project.id,
                }
                project.write({"participant_ids": [(0, 0, participant)]})

    # create an embedded version of the user input of presentation_video
    @api.onchange("presentation_video")
    def _compute_presentation_video_embed(self):
        if self.presentation_video:
            url_data = urlparse.urlparse(self.presentation_video)
            if "youtube" in url_data.hostname and "embed" not in url_data.path:
                query = urlparse.parse_qs(url_data.query)
                self.presentation_video_embed = "/".join(
                    [
                        url_data.scheme + "://" + url_data.hostname,
                        "embed",
                        query["v"][0],
                    ]
                )
            elif "vimeo" in url_data.hostname and "video" not in url_data.path:
                self.presentation_video_embed = "/".join(
                    [
                        url_data.scheme + "://player." + url_data.hostname,
                        "video",
                        url_data.path.lstrip("/"),
                    ]
                )
            else:
                self.presentation_video_embed = self.presentation_video
        else:
            self.presentation_video_embed = False

    def _compute_product_number_goal(self):
        for project in self:
            project.product_number_goal = sum(
                project.participant_ids.mapped("product_number_goal")
            )

    def _compute_product_number_reached(self):
        # Compute with SQL query for good performance
        self.env.cr.execute(
            """
            SELECT p.id, SUM(il.price_total), SUM(il.quantity)
            FROM account_move_line il
            JOIN crowdfunding_participant pa ON pa.id = il.crowdfunding_participant_id
            JOIN crowdfunding_project p ON p.id = pa.project_id
            WHERE il.payment_state = 'paid'
            AND p.id = ANY(%s)
            GROUP BY p.id
        """,
            [self.ids],
        )
        results = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}
        for project in self:
            res = results.get(project.id, (0, 0))
            project.amount_reached = round(res[0])
            project.product_number_reached = round(res[1])

    def _compute_number_sponsorships_goal(self):
        for project in self:
            project.number_sponsorships_goal = sum(
                project.participant_ids.mapped("number_sponsorships_goal")
            )
            project.number_csp_goal = sum(
                project.participant_ids.mapped("number_csp_goal")
            )

    def _compute_sponsorships(self):
        for project in self:
            project.sponsorship_ids = self.env["recurring.contract"].search(
                [
                    ("campaign_id", "=", project.campaign_id.id),
                    ("type", "like", "S"),
                    ("type", "!=", "CSP"),
                    ("state", "!=", "cancelled"),
                ]
            )

    def _compute_csp_sponsorships(self):
        for project in self:
            project.csp_sponsorship_ids = self.env["recurring.contract"].search(
                [
                    ("campaign_id", "=", project.campaign_id.id),
                    ("type", "=", "CSP"),
                    ("state", "!=", "cancelled"),
                ]
            )

    def _compute_number_sponsorships_reached(self):
        for project in self:
            project.number_sponsorships_reached = len(project.sponsorship_ids)
            project.number_csp_reached = len(project.csp_sponsorship_ids)

    def _compute_website_url(self):
        for project in self:
            project.website_url = f"/project/{project.id}"

    def _compute_time_left(self):
        for project in self:
            project.time_left = format_timedelta(
                project.deadline - date.today(), locale=self.env.lang[:2]
            )

    def _compute_owner_participant_id(self):
        for project in self:
            project.owner_participant_id = project.participant_ids.filtered(
                lambda participant, _project=project: participant.partner_id
                == _project.project_owner_id
            ).id

    def _compute_cover_photo_url(self):
        domain = self.env["website"].get_current_website()._get_http_domain()
        for project in self:
            project.cover_photo_url = (
                f"{domain}/web/content/crowdfunding.project/{project.id}/cover_photo"
            )

    def _compute_invoice_line_ids(self):
        for project in self:
            project.invoice_line_ids = self.env["account.move.line"].search(
                [("crowdfunding_participant_id", "in", project.participant_ids.ids)]
            )

    def validate(self):
        self.write({"state": "active", "is_published": True})
        comm_obj = self.env["partner.communication.job"]
        config = self.env.ref("crowdfunding_compassion.config_project_published")
        for project in self:
            # Send email to inform project owner
            comm_obj.create(
                {
                    "config_id": config.id,
                    "partner_id": project.project_owner_id.id,
                    "object_ids": project.id,
                }
            )

    @api.model
    def get_active_projects(
        self,
        limit=None,
        year=None,
        project_type=None,
        domain=None,
        offset=0,
        status="all",
    ):
        filters = list(
            filter(
                None,
                [
                    ("state", "!=", "draft"),
                    ("website_published", "=", True),
                    ("deadline", ">=", datetime(year, 1, 1)) if year else None,
                    ("create_date", "<=", datetime(year, 12, 31)) if year else None,
                    ("type", "=", project_type) if project_type else None,
                    ("deadline", ">=", date.today()) if status == "active" else None,
                    ("deadline", "<", date.today()) if status == "finish" else None,
                ],
            )
        )
        # only for active website
        if domain:
            filters += domain

        projects = self.search(
            filters, offset=offset, limit=limit, order="deadline DESC"
        )

        return projects

    def open_participants(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Participants"),
            "view_type": "form",
            "view_mode": "kanban,tree,form"
            if self.type == "collective"
            else "form,tree",
            "res_model": "crowdfunding.participant",
            "res_id": self.owner_participant_id.id,
            "domain": [("project_id", "=", self.id)],
            "target": "current",
            "context": self.env.context,
        }

    def open_donations(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Donations"),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.move.line",
            "domain": [("crowdfunding_participant_id", "in", self.participant_ids.ids)],
            "target": "current",
            "context": {
                "default_tree_view": self.env.ref(
                    "crowdfunding_compassion.donation_tree_view"
                ).id,
                "search_default_paid": True,
            },
        }

    def open_sponsorships(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Participants"),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "recurring.contract",
            "domain": [
                ("campaign_id", "=", self.campaign_id.id),
                ("type", "like", "S"),
            ],
            "target": "current",
        }

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = self.description
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = self.cover_photo_url
        res["default_opengraph"]["og:image:secure_url"] = self.cover_photo_url
        res["default_opengraph"]["og:image:type"] = "image/jpeg"
        res["default_opengraph"]["og:image:width"] = "640"
        res["default_opengraph"]["og:image:height"] = "442"
        return res

    @ormcache()
    def get_sponsor_card_header_image(self):
        return (
            ImageProcess(
                base64.b64encode(
                    file_open(
                        "crowdfunding_compassion/static/src/img/"
                        "sponsor_children_banner.jpg",
                        "rb",
                    ).read()
                ),
            )
            .resize(max_width=400)
            .image_base64(75)
        )

    @ormcache("value")
    def fund_impact_val_formatting(self, value):
        return format(value, ",d").replace(",", " ") if value > 9999 else value

    @ormcache()
    def sponsorship_card_content(self):
        value = sum(self.sudo().search([]).mapped("number_sponsorships_reached"))
        return {
            "type": "sponsorship",
            "value": self.fund_impact_val_formatting(value),
            "name": _("Sponsor children"),
            "text": _("sponsored children") if value > 1 else _("sponsored child"),
            "description": _(
                """
For 42 francs a month, you're opening the way out of poverty for a child. Sponsorship
 ensures that the child is known, loved and protected. In particular, it gives the child
 access to schooling, tutoring, regular balanced meals, medical care and training in the
 spiritual field, hygiene, etc. Every week, the child participates in the activities of
 one of the project center of the 8,000 local churches that are partners of
 Compassion. They allow him or her to discover and develop his or her talents."""
            ),
            "icon_image": self.get_sponsor_icon(),
            "header_image": self.get_sponsor_card_header_image(),
        }

    @ormcache()
    def get_sponsor_icon(self):
        return base64.b64encode(
            file_open(
                "crowdfunding_compassion/static/src/img/icn_children.png", "rb"
            ).read()
        )
