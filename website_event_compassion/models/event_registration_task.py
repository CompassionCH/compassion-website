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
    _name = "event.registration.task"
    _description = "Event registration task"
    _order = "sequence, name, id"

    name = fields.Char("Task", required=True, translate=True)
    sequence = fields.Integer(default=1)
    stage_id = fields.Many2one(
        "event.registration.stage",
        "Stage",
        required=True,
        help="Associate this task to this registration stage.",
        readonly=False,
    )
    default_task_url = fields.Char(
        help="Default URL for this task."
        "Can be overriden for each registration in the compute method of the "
        "related field."
    )
    website_published = fields.Boolean(
        "Published on website",
        help="If checked, this task will be visible on the website.",
    )
    open_new_tab = fields.Boolean(
        "Open in new tab",
        help="If checked, the task will open in a new tab.",
    )
    task_complete_on_click = fields.Boolean(
        "Complete on click",
        help="If checked, the task will be marked as done when clicked.",
    )


class EventRegistrationTaskRel(models.Model):
    # Helper class to link tasks to registrations with some custom attributes
    _name = "event.registration.task.rel"
    _description = "Event registration task relation"
    _order = "registration_id, done, sequence, id"

    task_id = fields.Many2one(
        "event.registration.task", "Task", required=True, index=True
    )
    registration_id = fields.Many2one(
        "event.registration", "Registration", required=True, index=True
    )
    stage_id = fields.Many2one(
        "event.registration.stage",
        related="task_id.stage_id",
    )
    sequence = fields.Integer(related="task_id.sequence", store=True)
    name = fields.Char(related="task_id.name")
    task_url = fields.Char(compute="_compute_task_url", compute_sudo=True)
    done = fields.Boolean()

    _sql_constraints = [
        (
            "task_registration_unique",
            "unique (task_id, registration_id)",
            "A task can be done only once per registration.",
        )
    ]

    def _compute_task_url(self):
        # Method can be inherited for specific task types
        for task in self:
            task.task_url = task.task_id.default_task_url

    def write(self, vals):
        # If the task is marked as done, check if we can move to the next stage
        super().write(vals)
        if vals.get("done"):
            self.mapped("registration_id").next_stage()
        return True
