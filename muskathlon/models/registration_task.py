from odoo import models

from odoo.addons.http_routing.models.ir_http import slug


class RegistrationTaskRel(models.Model):
    _inherit = "event.registration.task.rel"

    def _compute_task_url(self):
        super()._compute_task_url()
        task_musk_medic = self.env.ref("muskathlon.task_medical")
        task_charter = self.env.ref("muskathlon.task_sign_child_protection")
        task_flight = self.env.ref("muskathlon.task_flight_details")
        task_passport = self.env.ref("muskathlon.task_passport")
        for task in self:
            if task.task_id == task_musk_medic:
                survey = (
                    task.registration_id.medical_survey_id
                    or task.registration_id.event_id.medical_survey_id
                )
                task.task_url = (
                    survey.get_print_url() if task.done else survey.get_start_url()
                )
            elif task.task_id == task_charter:
                task.task_url = (
                    f"/partner/child-protection-charter?redirect="
                    f"/my/events/{slug(task.registration_id)}"
                )
            elif task.task_id == task_flight:
                task.task_url = f"/my/events/{slug(task.registration_id)}/flight"
            elif task.task_id == task_passport:
                task.task_url = f"/my/events/{slug(task.registration_id)}/passport"
