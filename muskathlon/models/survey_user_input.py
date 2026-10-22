##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Quentin Gigon <gigon.quentin@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import SUPERUSER_ID, models


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def write(self, vals):
        """
        Automatically complete Medical Survey task when user filled it
        """
        res = super().write(vals)
        if vals.get("state") == "done":
            # Search for Muskathlon medical surveys
            registrations = (
                self.env["event.registration"]
                .with_user(SUPERUSER_ID)
                .search(
                    [
                        ("partner_id", "in", self.mapped("partner_id").ids),
                        (
                            "event_id.event_type_id",
                            "=",
                            self.env.ref("muskathlon.event_type_muskathlon").id,
                        ),
                        (
                            "stage_id",
                            "=",
                            self.env.ref("muskathlon.stage_fill_profile").id,
                        ),
                    ]
                )
            )
            registrations.with_delay_sh(
                "muskathlon_medical_survey_done",
                priority=100,
                channel="root.partner_communication",
                identity_key=f"muskathlon.medical_survey.{registrations.ids}",
            )
        return res
