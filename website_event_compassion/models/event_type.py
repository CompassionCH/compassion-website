##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models

from odoo.addons.crm_compassion.models.event_compassion import EventCompassion


class EventType(models.Model):
    # Inherit from 'mail.thread' so that the followers can be notified when
    # events of the type have changed.
    _inherit = ["event.type", "mail.thread"]
    _name = "event.type"

    compassion_event_type = fields.Selection(
        EventCompassion.get_event_types, required=True
    )
    stage_ids = fields.Many2many(
        "event.registration.stage", "event_registration_stage_to_type_rel"
    )
    medical_survey_id = fields.Many2one("survey.survey", "Medical survey")
    feedback_survey_id = fields.Many2one("survey.survey", "Feedback survey")
