##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, fields, models

from odoo.addons.event.models.event_mail import _INTERVALS


class EventTypeMail(models.Model):
    _inherit = "event.type.mail"

    notification_type = fields.Selection(
        selection_add=[("communication", "Communication rule")],
        ondelete={"communication": "set default"},
        default="communication",
    )
    communication_id = fields.Many2one(
        "partner.communication.config",
        "Communication",
        domain=[("model_id.model", "=", "event.registration")],
        readonly=False,
    )

    @api.model
    def _get_event_mail_fields_whitelist(self):
        return super()._get_event_mail_fields_whitelist() + ["communication_id"]

    @api.onchange("notification_type", "communication_id")
    def onchange_communication_rule(self):
        if self.notification_type == "communication" and self.communication_id:
            self.template_id = self.communication_id.email_template_id


class EventMail(models.Model):
    _inherit = "event.mail"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    communication_id = fields.Many2one(
        "partner.communication.config",
        "Communication",
        domain=[("model_id.model", "=", "event.registration")],
        readonly=False,
    )
    notification_type = fields.Selection(
        selection_add=[("communication", "Communication rule")],
        ondelete={"communication": "set default"},
        default="communication",
    )
    template_id = fields.Many2one(
        related="communication_id.email_template_id", readonly=False
    )
    interval_type = fields.Selection(
        selection_add=[("after_stage", "After stage")],
        ondelete={"after_stage": "set default"},
    )
    stage_id = fields.Many2one("event.registration.stage", "Stage", readonly=False)

    event_type_id = fields.Many2one("event.type", readonly=False)
    event_id = fields.Many2one(required=False, readonly=False)

    @api.depends(
        "event_id.date_begin",
        "interval_type",
        "interval_unit",
        "interval_nbr",
    )
    def _compute_scheduled_date(self):
        """Add computation for after_stage interval type"""
        for scheduler in self:
            if scheduler.interval_type == "after_stage":
                scheduler.scheduled_date = scheduler.event_id.create_date
            else:
                super(EventMail, scheduler)._compute_scheduled_date()

    @api.onchange("notification_type", "communication_id")
    def onchange_communication_rule(self):
        if self.notification_type == "communication" and self.communication_id:
            self.template_id = self.communication_id.email_template_id

    def execute(self):
        """
        Replace execute method to use after_stage interval_type and
        partner communication jobs instead of mail_templates
        :return: True
        """
        for mail in self:
            now = fields.Datetime.now()
            if mail.interval_type == "after_stage":
                # update registration lines
                lines = [
                    (0, 0, {"registration_id": registration.id})
                    for registration in (
                        mail.event_id.registration_ids
                        - mail.mapped("mail_registration_ids.registration_id")
                    )
                ]
                if lines:
                    mail.write({"mail_registration_ids": lines})
                # execute scheduler on registrations
                mail.mail_registration_ids.execute()
            else:
                # Do not send emails if the mailing was scheduled before the event
                # but the event is over
                if (
                    not mail.mail_sent
                    and mail.scheduled_date <= now
                    and mail.notification_type == "communication"
                    and (
                        mail.interval_type != "before_event"
                        or mail.event_id.date_end > now
                    )
                ):
                    mail.event_id.send_communication(mail.communication_id.id)
                    mail.write({"mail_sent": True})
        return super().execute()


class EventMailRegistration(models.Model):
    _inherit = "event.mail.registration"

    @api.depends(
        "registration_id",
        "registration_id.stage_date",
        "scheduler_id.interval_unit",
        "scheduler_id.interval_type",
    )
    def _compute_scheduled_date(self):
        """
        Add computation of scheduled date if interval type is after stage
        :return:
        """
        for mail in self:
            if mail.scheduler_id.interval_type == "after_stage":
                registration = mail.registration_id
                scheduler = mail.scheduler_id
                if registration.stage_id == scheduler.stage_id:
                    date_open = registration.stage_date
                    mail.scheduled_date = date_open + _INTERVALS[
                        scheduler.interval_unit
                    ](scheduler.interval_nbr)
                else:
                    mail.scheduled_date = False
            else:
                super(EventMailRegistration, mail)._compute_scheduled_date()

    def execute(self):
        now = fields.Datetime.now()
        todo = self.filtered(
            lambda reg_mail: not reg_mail.mail_sent
            and reg_mail.registration_id.state in ["open", "done"]
            and (reg_mail.scheduled_date and reg_mail.scheduled_date <= now)
            and reg_mail.scheduler_id.notification_type == "communication"
        )
        for reg_mail in todo:
            reg_mail.registration_id.send_communication(
                reg_mail.scheduler_id.communication_id.id
            )
        todo.write({"mail_sent": True})
        return super().execute()
