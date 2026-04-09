##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Nicolas Badoux <n.badoux@hotmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import file_open

from .event_compassion import EventCompassion


class MuskathlonRegistration(models.Model):
    _name = "event.registration"
    _inherit = "event.registration"

    is_muskathlon = fields.Boolean(related="compassion_event_id.is_muskathlon")
    sport_discipline_id = fields.Many2one(
        "sport.discipline", "Sport discipline", readonly=False
    )
    sport_level = fields.Selection(EventCompassion.get_sport_levels)
    sport_level_description = fields.Text("Describe your sport experience")
    t_shirt_size = fields.Selection(EventCompassion.get_t_shirt_sizes)
    is_in_two_months = fields.Boolean(compute="_compute_is_in_two_months")
    thank_you_quote = fields.Html(
        compute="_compute_thank_you_quote",
        help="Used in thank you letters for donations linked to an event "
        "and to this partner.",
    )
    comments = fields.Text("Registration Comments")

    _sql_constraints = [
        (
            "reg_unique",
            "unique(event_id,partner_id)",
            "Only one registration per participant/event is allowed!",
        )
    ]

    def _compute_thank_you_quote(self):
        html_file = file_open(
            "partner_compassion/static/src/html/thank_you_quote_template.html"
        )
        template_html = str(html_file.read())
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for registration in self:
            partner = registration.partner_id
            firstname = partner.firstname
            lastname = partner.lastname
            html_vals = {
                "img_alt": registration.display_name,
                "image_url": f"{base_url}/web/image"
                f"/event.registration/{registration.id}"
                f"/profile_picture/500x200/{firstname}.jpg",
                "text": registration.ambassador_quote.strip() or "",
                "attribution": _("Quote from %s %s") % (firstname, lastname)
                if registration.ambassador_quote.strip()
                else "",
            }
            registration.thank_you_quote = template_html.format(**html_vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Override to add specific behavior for Muskathlon registration.
        - Set stage to unconfirmed for Muskathlon events
        - Notify user for registration
        - Check if the partner has signed the child protection charter
        - Check if the partner has activated his account
        """
        for vals in vals_list:
            event = self.env["event.event"].browse(vals.get("event_id"))
            if event.compassion_event_id.is_muskathlon:
                vals["stage_id"] = self.env.ref("muskathlon.stage_unconfirmed").id
        registrations = super().create(vals_list)
        for registration in registrations.filtered("is_muskathlon"):
            partner = registration.partner_id
            if partner.date_agreed_child_protection_charter:
                task = self.env.ref("muskathlon.task_sign_child_protection")
                registration.task_ids.filtered(
                    lambda t, m_task=task: t.task_id == m_task
                ).write({"done": True})
            if partner.user_ids and any(partner.mapped("user_ids.login_date")):
                task = self.env.ref("muskathlon.task_activate_account")
                registration.task_ids.filtered(
                    lambda t, m_task=task: t.task_id == m_task
                ).write({"done": True})
            registration.notify_muskathlon_registration()
        return registrations

    def _compute_is_in_two_months(self):
        """this function defines if the boolean hides or shows the survey"""
        for registration in self:
            today = datetime.datetime.today()
            start_day = registration.event_begin_date
            delta = start_day - today
            registration.is_in_two_months = delta.days < 60

    def _inverse_passport(self):
        super()._inverse_passport()
        task_passport = self.env.ref("muskathlon.task_passport")
        for registration in self.filtered("passport"):
            registration.task_ids.filtered(lambda t: t.task_id == task_passport).write(
                {"done": True}
            )

    @api.onchange("event_id")
    def onchange_event_id(self):
        return {
            "domain": {
                "sport_discipline_id": [
                    ("id", "in", self.compassion_event_id.sport_discipline_ids.ids)
                ]
            }
        }

    @api.onchange("sport_discipline_id")
    def onchange_sport_discipline(self):
        if (
            self.sport_discipline_id
            and self.sport_discipline_id
            not in self.compassion_event_id.sport_discipline_ids
        ):
            self.sport_discipline_id = False
            return {
                "warning": {
                    "title": _("Invalid sport"),
                    "message": _("This sport is not in muskathlon"),
                }
            }

    def notify_muskathlon_registration(self):
        """Notify user for registration"""
        partners = self.mapped("user_id.partner_id") | self.event_id.mapped(
            "message_partner_ids"
        )
        self.message_subscribe(partners.ids)

        subtype_id = self.env.ref("website_event_compassion.mt_registration_create").id

        for registration in self:
            registration.message_post_with_source(
                "muskathlon.muskathlon_registration_notification_view",
                subject=_("%s - New Muskathlon registration") % registration.name,
                render_values={"object": registration},
                message_type="comment",
                subtype_id=subtype_id,
            )

        return True

    def muskathlon_medical_survey_done(self):
        task_medical = self.env.ref("muskathlon.task_medical")
        self.mapped("task_ids").filtered(lambda t: t.task_id == task_medical).write(
            {"done": True}
        )
        for registration in self:
            user_input = self.env["survey.user_input"].search(
                [
                    ("partner_id", "=", registration.partner_id.id),
                    ("survey_id", "=", registration.event_id.medical_survey_id.id),
                ],
                limit=1,
                order="start_datetime desc",
            )
            template = self.env.ref(
                "muskathlon.medical_survey_to_doctor_template"
            ).sudo()
            try:
                template.send_mail(
                    user_input.id,
                    force_send=True,
                )
            except UserError:
                continue
        return True
