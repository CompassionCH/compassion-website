##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Event(models.Model):
    _inherit = ["event.event", "translatable.model", "mail.activity.mixin"]
    _name = "event.event"

    compassion_event_id = fields.Many2one(
        "crm.event.compassion", "Event", readonly=False
    )
    reminder_config_id = fields.Many2one(related="event_type_id.reminder_config_id")
    participants_amount_objective = fields.Integer(
        "Default raise objective by participant", default=10000
    )
    custom_amount_objective = fields.Boolean(
        "Participant can set his raising objective"
    )
    fundraising = fields.Boolean(
        "Activate fundraising for participants",
        help="If activated, the participants will have a user account where "
        "they can keep track of their donations. They will have a "
        "profile page on the website where people can donate.",
    )
    donation_product_id = fields.Many2one(
        "product.product", "Donation product", readonly=False
    )
    sponsorship_donation_value = fields.Monetary(
        "Sponsorship to donation conversion",
        default=1000,
        help="This sets how much the barometer of the participant will be "
        "raised when a sponsorship is made for him.",
    )
    registration_open = fields.Boolean(compute="_compute_registration_open")
    registration_closed = fields.Boolean(compute="_compute_registration_closed")
    registration_not_started = fields.Boolean(
        compute="_compute_registration_not_started"
    )
    registration_full = fields.Boolean(compute="_compute_registration_full")
    medical_survey_id = fields.Many2one(
        "survey.survey",
        "Medical Survey",
        readonly=False,
        compute="_compute_surveys",
        store=True,
    )
    feedback_survey_id = fields.Many2one(
        "survey.survey",
        "Feedback Survey",
        readonly=False,
        compute="_compute_surveys",
        store=True,
    )

    @api.depends("registration_ids.state", "registration_ids.active")
    def _compute_seats(self):
        """Unconfirmed registrations from the website are counted in the
        attendees, but they don't take a seat until they are confirmed."""
        super()._compute_seats()
        draft_count = dict(
            self.env["event.registration"]._read_group(
                [("event_id", "in", self.ids), ("state", "=", "draft")],
                ["event_id"],
                ["__count"],
            )
        )
        for event in self:
            event.seats_taken += draft_count.get(event._origin, 0)

    def _compute_registration_open(self):
        event_announced = self.env.ref("event.event_stage_announced")
        for event in self:
            start_date = event.date_begin
            event.registration_open = (
                event.stage_id == event_announced and datetime.now() < start_date
            )

    def _compute_registration_closed(self):
        event_ended = self.env.ref("event.event_stage_done")
        for event in self:
            event.registration_closed = (
                event.stage_id == event_ended or event.date_begin < datetime.now()
            )

    def _compute_registration_not_started(self):
        new = self.env.ref("event.event_stage_new")
        booked = self.env.ref("event.event_stage_booked")
        for event in self:
            event.registration_not_started = (
                event.stage_id in (new, booked) and datetime.now() < event.date_begin
            )

    def _compute_registration_full(self):
        for event in self:
            event.registration_full = (
                event.seats_limited
                and event.seats_available <= 0
                and datetime.now() < event.date_begin
            )

    @api.depends("event_type_id")
    def _compute_surveys(self):
        for event in self:
            medical_survey = event.event_type_id.medical_survey_id
            feedback_survey = event.event_type_id.feedback_survey_id
            if medical_survey != event.medical_survey_id:
                event.medical_survey_id = medical_survey
            if feedback_survey != event.feedback_survey_id:
                event.feedback_survey_id = feedback_survey

    def action_send_reminder(self):
        """Remind the participants who still have something to do on their
        My events page."""
        for event in self:
            event.registration_ids.send_communication(
                event.reminder_config_id.id,
                filter_func=lambda reg: (
                    reg.state not in ("cancel", "done") and reg.incomplete_task_count
                ),
            )
        return True

    def _sync_template_mails(self, configs):
        """Give the events the template's rules of the given communications,
        or remove them when the template no longer has one. The other rules
        of the events (e.g. a communication made for one event) are kept.

        The participants already in (or past) the stage of a rule sent after
        a stage don't get it late.
        """
        for event in self:
            rules = event.event_type_id.event_type_mail_ids
            for config in configs:
                rule = rules.filtered(lambda mail, c=config: mail.communication_id == c)
                scheduler = event.event_mail_ids.filtered(
                    lambda mail, c=config: mail.communication_id == c
                )
                if not rule:
                    scheduler.unlink()
                    continue
                values = rule[:1]._prepare_event_mail_values()
                if scheduler:
                    scheduler.write(values)
                else:
                    scheduler = self.env["event.mail"].create(
                        dict(values, event_id=event.id)
                    )
                for stage_scheduler in scheduler.filtered(
                    lambda mail: mail.interval_type == "after_stage"
                ):
                    passed = event.registration_ids.filtered(
                        lambda reg, stage=stage_scheduler.stage_id: (
                            reg.stage_id.sequence >= stage.sequence
                            or reg.state == "cancel"
                        )
                    )
                    self.env["event.mail.registration"].create(
                        [
                            {
                                "scheduler_id": stage_scheduler.id,
                                "registration_id": reg.id,
                                "mail_sent": True,
                            }
                            for reg in passed
                            - stage_scheduler.mail_registration_ids.registration_id
                        ]
                    )
        return True

    def _registration_stages(self):
        """Stages of this event's template, narrowed to its type of trip."""
        self.ensure_one()
        trip_type = self.compassion_event_id.trip_type_id
        return self.event_type_id.stage_ids.filtered(
            lambda stage: not stage.trip_type_ids or trip_type in stage.trip_type_ids
        )

    def send_communication(
        self,
        config_id,
        force_send=False,
        filter_func=lambda self: self.state != "cancel",
    ):
        """
        Send a communication rule to all attendees of the event
        :param config_id: communication config id
        :param force_send: if True, send the communication immediately regardless of
                           its send_mode
        :param filter_func: filter function to apply on the registrations
        :return: communication jobs
        """
        return self.registration_ids.send_communication(
            config_id, force_send, filter_func
        )

    def button_print_medical_surveys(self):
        if self.medical_survey_id:
            return self.medical_survey_id.action_result_survey()
        else:
            raise UserError(_("There is no medical survey to print"))

    def button_print_feedback_surveys(self):
        if self.feedback_survey_id:
            return self.feedback_survey_id.action_result_survey()
        else:
            raise UserError(_("There is no feedback survey to print"))
