##############################################################################
#
#    Copyright (C) 2024 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class PartnerCoordinatesForm(models.TransientModel):
    _name = "cms.form.crowdfunding.project.update"
    _description = "Crowdfunding project update"

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
    twitter_url = fields.Char("X link")
    instagram_url = fields.Char("Instagram link")
    personal_web_page_url = fields.Char("Personal web page")
    project_id = fields.Many2one("crowdfunding.project", required=True)

    def create(self, vals_list):
        wizard = super().create(vals_list)
        project = wizard.project_id
        project_vals = {
            key: value for key, value in wizard.read([])[0].items() if value
        }
        if project_vals.get("name") or project_vals.get("description"):
            # Notify responsible for the changes, for validation.
            settings = self.env["res.config.settings"].sudo()
            notify_ids = settings.get_param("new_participant_notify_ids")
            if notify_ids:
                user = (
                    self.env["res.partner"]
                    .sudo()
                    .browse(notify_ids[0][2])
                    .mapped("user_ids")[:1]
                )
                project.sudo().activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary="Verify project information.",
                    note=f"{project.project_owner_id.name} updated the "
                    f"name and description of the project. "
                    f"Please check if the information is good enough and "
                    f"verify the translations.",
                    user_id=user.id,
                )
        del project_vals["id"]
        del project_vals["project_id"]
        project.write(project_vals)
        return wizard
