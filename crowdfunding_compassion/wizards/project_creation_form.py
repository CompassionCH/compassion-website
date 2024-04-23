##############################################################################
#
#    Copyright (C) 2020-2024 Compassion CH (http://www.compassion.ch)
#    @author: Quentin Gigon <gigon.quentin@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from base64 import b64encode
from datetime import datetime

from odoo import _, fields, models
from odoo.http import request
from odoo.tools import file_open

from ..exceptions import (
    InvalidDeadlineException,
    NoGoalException,
    NoProjectException,
)

_logger = logging.getLogger(__name__)


class ProjectCreationFormStep1(models.TransientModel):
    _name = "cms.form.crowdfunding.project.step1"
    _description = "Crowdfunding project creation wizard - Step 1"

    name = fields.Char(
        "Name of your project",
        help="Use a catchy name that is accurate to your idea.",
        required=True,
    )
    description = fields.Text(
        "Project description",
        help="Aim of the project, why you want to create it, for which purpose and "
        "any useful information that the donors should know.",
        required=True,
    )
    deadline = fields.Date(
        "Deadline of project",
        help="Indicate when your project should end.",
        required=True,
    )
    cover_photo = fields.Image(
        "Cover Photo",
        help="Upload a cover photo that represents your project. Best size: 900x400px",
        required=False,
        max_width=1024,
        max_height=512,
    )
    presentation_video = fields.Char(
        help="Paste any video link that showcase your project"
        " (e.g. https://vimeo.com/jlkj34ek5)"
    )
    type = fields.Selection(
        [("individual", "Individual"), ("collective", "Collective")],
        required=True,
        default="individual",
    )
    facebook_url = fields.Char("Facebook link")
    twitter_url = fields.Char("Twitter link")
    instagram_url = fields.Char("Instagram link")
    personal_web_page_url = fields.Char("Personal web page")

    def create(self, vals):
        deadline = fields.Date.from_string(vals["deadline"])
        if deadline < datetime.now().date():
            raise InvalidDeadlineException
        wizard = super().create(vals)
        request.session.update({"project_creation_step1": wizard.id})
        return wizard


class ProjectCreationStep2(models.TransientModel):
    _name = "cms.form.crowdfunding.project.step2"
    _description = "Crowdfunding project creation wizard - Step 2"

    number_sponsorships_goal = fields.Integer()
    number_csp_goal = fields.Integer()
    product_number_goal = fields.Integer()
    product_id = fields.Many2one(
        "product.product",
        domain=[("activate_for_crowdfunding", "=", True)],
    )
    project_id = fields.Many2one("crowdfunding.project")

    PARTICIPANT_FINAL_FIELDS = [
        "product_number_goal",
        "number_sponsorships_goal",
        "number_csp_goal",
    ]

    def create(self, vals_list):
        product_goal = vals_list.get("product_number_goal", 0)
        sponsorship_goal = vals_list.get("number_sponsorships_goal", 0)
        csp_goal = vals_list.get("number_csp_goal", 0)

        # Projects must have either a positive sponsorship or fund objective
        if not product_goal and not sponsorship_goal and not csp_goal:
            raise NoGoalException

        if not product_goal:
            vals_list["product_id"] = False
        if product_goal and vals_list["product_id"]:
            product = self.env["product.product"].sudo().browse(vals_list["product_id"])
            if product.impact_type == "large":
                vals_list["product_number_goal"] = product_goal * 100
        res = super().create(vals_list)
        request.session.update({"project_creation_step2": res.id})
        return res


class ProjectCreationStep3(models.TransientModel):
    _name = "cms.form.crowdfunding.project.step3"
    _inherit = "cms.form.partner"
    _description = "Crowdfunding project creation wizard - Step 3"

    name = fields.Char()
    partner_image_1920 = fields.Image(
        "Profile picture",
        help="Upload a profile picture, square 800 x 800px",
        max_width=1920,
        max_height=1920,
    )
    personal_motivation = fields.Text(
        "Personal motivation",
        help="Tell the others what is inspiring you, why it matters to you.",
        required=True,
    )
    facebook_url = fields.Char("Facebook link")
    twitter_url = fields.Char("Twitter link")
    instagram_url = fields.Char("Instagram link")
    personal_web_page_url = fields.Char("Personal web page")
    nickname = fields.Char(
        "Name of your group / organisation",
        help="This name will be display instead of your name.",
    )
    step1_id = fields.Many2one("cms.form.crowdfunding.project.step1")
    step2_id = fields.Many2one("cms.form.crowdfunding.project.step2", required=True)

    # Make address fields mandatory
    partner_street = fields.Char(required=True)
    partner_zip = fields.Char(required=True)
    partner_city = fields.Char(required=True)
    partner_phone = fields.Char(required=True)

    PARTICIPANT_FINAL_FIELDS = [
        "name",
        "nickname",
        "personal_motivation",
        "facebook_url",
        "twitter_url",
        "instagram_url",
        "personal_web_page_url",
    ]

    def create(self, vals_list):
        # Take values from previous steps
        vals_list["step1_id"] = request.session.get("project_creation_step1")
        try:
            vals_list["step2_id"] = request.session.get("project_creation_step2")
        except KeyError as err:
            raise NoProjectException from err
        # Allow updating any matched partner values
        vals_list["match_update"] = True
        step3_record = super().create(vals_list)
        if step3_record.step1_id:
            project = step3_record.create_project().sudo()
            config = self.env.ref(
                "crowdfunding_compassion.config_project_confirmation"
            ).sudo()
        else:
            project = step3_record.join_project().project_id.sudo()
            config = self.env.ref("crowdfunding_compassion.config_project_join").sudo()
        step3_record.notify_new_participant(config, project)
        # Empty the session
        request.session.pop("project_creation_step1", False)
        request.session.pop("project_creation_step2", False)
        return step3_record

    def create_project(self):
        """Called for new project.
        Create as root and avoid putting Admin as follower."""
        self.name = f"{self.step1_id.name} - {self.partner_id.preferred_name}"
        participant_vals = self._get_participant_vals()
        project_vals = self.step1_id.read()[0]
        project_vals.pop("id")
        project_vals.update(
            {
                "project_owner_id": self.partner_id.id,
                "participant_ids": [(0, 0, participant_vals)],
                "product_id": self.step2_id.product_id.id,
            }
        )
        project_vals["project_owner_id"] = self.partner_id.id
        project_vals["participant_ids"] = [(0, 0, participant_vals)]
        return (
            self.env["crowdfunding.project"]
            .sudo()
            .with_context(tracking_disable=True)
            .create(project_vals)
        )

    def join_project(self):
        """This is called when project already exists and participant is joining."""
        self.name = (
            f"{self.step2_id.project_id.name} - {self.partner_id.preferred_name}"
        )
        participant_vals = self._get_participant_vals()
        return (
            self.env["crowdfunding.participant"]
            .sudo()
            .with_context(tracking_disable=True)
            .create(participant_vals)
        )

    def _get_participant_vals(self):
        vals = self.read(self.PARTICIPANT_FINAL_FIELDS)[0]
        vals.update(self.step2_id.read(self.step2_id.PARTICIPANT_FINAL_FIELDS)[0])
        if self.step2_id.project_id:
            vals["project_id"] = self.step2_id.project_id.id
        partner = self.partner_id
        vals["partner_id"] = partner.id
        if not partner.image_512:
            path = "crowdfunding_compassion/static/src/img/guy.png"
            if partner.title.gender == "F":
                path = "crowdfunding_compassion/static/src/img/lady.png"
            partner.write({"image_1920": b64encode(file_open(path, "rb").read())})
        return vals

    def notify_new_participant(self, config, project):
        comm_obj = self.env["partner.communication.job"].sudo()
        comm_obj.create(
            {
                "config_id": config.id,
                "partner_id": self.partner_id.id,
                "object_ids": project.id,
            }
        )

        # Notify staff of new participant
        settings = self.env["res.config.settings"].sudo()
        notify_ids = settings.get_param("new_participant_notify_ids")
        if notify_ids:
            user = (
                self.env["res.partner"]
                .sudo()
                .browse(notify_ids[0][2])
                .mapped("user_ids")[:1]
            )
            self.partner_id.sudo().activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("New Crowdfunding participant"),
                note=_(
                    "%s created or joined a project. "
                    "A user may need to be created if he doesn't have access"
                )
                % self.partner_id.name,
                user_id=user.id,
            )
