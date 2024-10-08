#    Copyright (C) 2020 Compassion CH
#    @author: Quentin Gigon
from werkzeug.urls import url_encode, url_parse

from odoo import _, api, fields, models
from odoo.tools import file_open

from ..exceptions import NoGoalException


class CrowdfundingParticipant(models.Model):
    _name = "crowdfunding.participant"
    _description = "Participant to one of our crowd-fundings"
    _inherit = ["website.seo.metadata", "website.published.multi.mixin", "mail.thread"]
    _inherits = {"utm.source": "source_id"}
    _order = "project_id desc, name asc"

    project_id = fields.Many2one(
        "crowdfunding.project",
        index=True,
        ondelete="cascade",
        string="Project",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Partner", required=True, index=True, ondelete="cascade"
    )
    nickname = fields.Char(
        "Name of your group / organisation",
        help="This name will be display instead of your name.",
    )
    personal_motivation = fields.Text(translate=True)
    product_number_goal = fields.Integer(default=0)
    product_number_reached = fields.Integer(compute="_compute_product_number_reached")
    number_sponsorships_goal = fields.Integer(default=0)
    number_sponsorships_reached = fields.Integer(
        compute="_compute_number_sponsorships_reached"
    )
    number_csp_goal = fields.Integer(default=0)
    number_csp_reached = fields.Integer(compute="_compute_number_sponsorships_reached")
    sponsorship_ids = fields.Many2many(
        "recurring.contract", compute="_compute_sponsorships", string="Sponsorships"
    )
    csp_sponsorship_ids = fields.Many2many(
        "recurring.contract",
        compute="_compute_csp_sponsorships",
        string="CSP Sponsorships",
    )
    invoice_line_ids = fields.One2many(
        "account.move.line", "crowdfunding_participant_id", string="Donations"
    )
    source_id = fields.Many2one(
        "utm.source", "UTM Source", required=True, ondelete="cascade"
    )
    facebook_url = fields.Char(string="Facebook link")
    twitter_url = fields.Char(string="X link")
    instagram_url = fields.Char(string="Instagram link")
    personal_web_page_url = fields.Char(string="Personal web page")
    profile_photo = fields.Image(related="partner_id.image_512")
    profile_photo_url = fields.Char(compute="_compute_profile_photo_url")
    sponsorship_url = fields.Char(compute="_compute_sponsorship_url")
    survival_sponsorship_url = fields.Char(compute="_compute_sponsorship_url")
    is_published = fields.Boolean(related="project_id.is_published", store=True)
    website_id = fields.Many2one("website", related="project_id.website_id", store=True)
    thank_you_quote = fields.Html(
        compute="_compute_thank_you_quote",
        help="Used in thank you letters for donations linked to an event "
        "and to this partner.",
    )


    # kanban colors
    color_sponsorship = fields.Char(compute="_compute_color_sponsorship")
    color_product = fields.Char(compute="_compute_color_product")
    color = fields.Integer()

    _sql_constraints = [
        (
            "registration_unique",
            "unique(project_id,partner_id)",
            "Only one registration per participant/project is allowed!",
        )
    ]

    @api.constrains(
        "number_sponsorships_goal", "number_csp_goal", "product_number_goal"
    )
    def _check_goals(self):
        for participant in self:
            if (
                participant.number_sponsorships_goal == 0
                and participant.number_csp_goal == 0
                and participant.product_number_goal == 0
            ):
                raise NoGoalException

    @api.model
    def create(self, vals):
        partner = self.env["res.partner"].browse(vals.get("partner_id"))
        project = self.env["crowdfunding.project"].browse(vals.get("project_id"))
        vals["name"] = f"{project.name} - {partner.preferred_name}"
        return super().create(vals)

    @api.model
    def get_sponsorship_url(self, participant_id):
        return self.browse(participant_id).sudo().sponsorship_url

    def _compute_thank_you_quote(self):
        html_file = file_open(
            "partner_compassion/static/src/html/thank_you_quote_template.html"
        )
        template_html = str(html_file.read())
        for details in self:
            firstname = details.partner_id.firstname
            lastname = details.partner_id.lastname
            html_vals = {
                "img_alt": details.display_name,
                "image_data": details.partner_id.with_context(
                    bin_size=False
                ).image_512.decode("utf-8"),
                "text": details.personal_motivation.strip() or "",
                "attribution": _("Quote from %s %s") % (firstname, lastname)
                if details.personal_motivation.strip()
                else "",
            }
            details.thank_you_quote = template_html.format(**html_vals)

    def _compute_sponsorship_url(self):
        wp = self.env["wordpress.configuration"].sudo().get_config()
        for participant in self:
            query = url_encode(
                {
                    "utm_medium": "Crowdfunding",
                    "utm_campaign": participant.project_id.name,
                    "utm_source": participant.name,
                }
            )
            parsed_csp_url = url_parse(
                f"https://{wp.host}{wp.survival_sponsorship_url}"
            )
            participant.sponsorship_url = f"/children?{query}"
            participant.survival_sponsorship_url = parsed_csp_url.replace(
                query=query
            ).to_url()

    def _compute_product_number_reached(self):
        for participant in self:
            invl = participant.invoice_line_ids.filtered(
                lambda line: line.payment_state == "paid"
            )
            price_total = sum(invl.mapped("price_total"))
            participant.product_number_reached = round(
                price_total / participant.project_id.product_price
            )

    def _compute_sponsorships(self):
        for participant in self:
            participant.sponsorship_ids = self.env["recurring.contract"].search(
                [
                    ("source_id", "=", participant.source_id.id),
                    ("type", "like", "S"),
                    ("type", "!=", "CSP"),
                    ("state", "!=", "cancelled"),
                ]
            )

    def _compute_csp_sponsorships(self):
        for participant in self:
            participant.csp_sponsorship_ids = self.env["recurring.contract"].search(
                [
                    ("source_id", "=", participant.source_id.id),
                    ("type", "=", "CSP"),
                    ("state", "!=", "cancelled"),
                ]
            )

    def _compute_number_sponsorships_reached(self):
        for participant in self:
            participant.number_sponsorships_reached = len(participant.sponsorship_ids)
            participant.number_csp_reached = len(participant.csp_sponsorship_ids)

    def _compute_profile_photo_url(self):
        domain = self.env["website"].get_current_website()._get_http_domain()
        for participant in self:
            title = participant.sudo().partner_id.title.with_context(lang="en_US")
            if participant.profile_photo:
                path = (
                    f"web/content/crowdfunding.participant"
                    f"/{participant.id}/profile_photo"
                )
            elif title.name == "Mister":
                path = "crowdfunding_compassion/static/src/img/guy.png"
            elif title.name == "Madam":
                path = "crowdfunding_compassion/static/src/img/lady.png"
            else:
                path = None

            participant.profile_photo_url = f"{domain}/{path}" if path else path

    def _compute_website_url(self):
        for participant in self:
            participant.website_url = f"/participant/{participant.id}"

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

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = self.personal_motivation
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = self.profile_photo_url
        res["default_opengraph"]["og:image:secure_url"] = self.profile_photo_url
        res["default_opengraph"]["og:image:type"] = "image/jpeg"
        res["default_opengraph"]["og:image:width"] = "640"
        res["default_opengraph"]["og:image:height"] = "442"
        return res
