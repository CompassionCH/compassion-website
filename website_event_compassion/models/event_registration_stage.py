##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models


class EventStage(models.Model):
    _name = "event.registration.stage"
    _description = "Event registration stage"
    _order = "sequence, name, id"

    name = fields.Char("Stage name", required=True, translate=True)
    sequence = fields.Integer(default=1, help="Used to order stages. Lower is better.")
    duration = fields.Integer(
        help="Set a maximum duration (in days) after which the registration "
        "will be shown in red in the kanban view."
    )
    event_type_ids = fields.Many2many(
        "event.type",
        "event_registration_stage_to_type_rel",
        string="Event types",
        ondelete="cascade",
        help="Specific event types that use this stage. "
        "Other event types will not be able to see or use this stage.",
        readonly=False,
    )
    task_ids = fields.One2many("event.registration.task", "stage_id", "Tasks")
    fold = fields.Boolean(
        "Folded in Pipeline",
        help="This stage is folded in the kanban view when there are no "
        "records in that stage to display.",
    )
    registration_state = fields.Selection(
        [
            ("draft", "Unconfirmed"),
            ("open", "Confirmed"),
            ("done", "Attended"),
            ("cancel", "Cancelled"),
        ],
        help="If set, this will set automatically the registration to the chosen "
        "state when it reaches this stage.",
    )
