from odoo import _
from odoo.exceptions import UserError


class InvalidDeadlineException(UserError):
    def __init__(self):
        super().__init__(_("The deadline must be in the future."))


class NoGoalException(UserError):
    def __init__(self):
        super().__init__(_("At least one goal must be set."))


class NoProjectException(UserError):
    def __init__(self):
        super().__init__(
            _(
                "No project was defined during the previous steps. "
                "Please restart the registration process."
            )
        )
