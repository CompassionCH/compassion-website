##############################################################################
#
#    Copyright (C) 2024 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class CrowdfundingParticipatUpdateForm(models.TransientModel):
    _name = "cms.form.crowdfunding.participant.update"

    profile_photo = fields.Image(
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
    participant_id = fields.Many2one("crowdfunding.participant", required=True)

    def create(self, vals_list):
        # Update the participant
        wizard = super().create(vals_list)
        participant = wizard.participant_id
        participant_vals = {
            key: value for key, value in wizard.read([])[0].items() if value
        }
        del participant_vals["id"]
        del participant_vals["participant_id"]
        participant.write(participant_vals)
        return wizard
