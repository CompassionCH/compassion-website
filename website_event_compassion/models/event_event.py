##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError


class Event(models.Model):
    _inherit = ["event.event", "translatable.model", "mail.activity.mixin"]
    _name = "event.event"

    compassion_event_id = fields.Many2one(
        "crm.event.compassion", "Event", readonly=False
    )
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
        "survey.survey", "Medical Survey", readonly=False
    )
    feedback_survey_id = fields.Many2one(
        "survey.survey", "Feedback Survey", readonly=False
    )

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
