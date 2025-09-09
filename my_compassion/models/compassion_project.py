##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.addons.message_center_compassion.tools.onramp_connector import OnrampConnector

logger = logging.getLogger(__name__)

try:
    from pytz import timezone
except (OSError, ImportError):
    logger.warning("Please install pytz")


class CompassionProject(models.Model):
    _inherit = "compassion.project"

    supported_types = ["cognitive", "physical", "socio", "spiritual"]

    center_current_time = fields.Datetime(
        string='Current Time',
        compute='_compute_current_time'
    )

    def get_activity_for_age(self, age, activity_type="physical"):
        if activity_type and activity_type not in self.supported_types:
            raise ValueError(
                f"Type {activity_type} is not supported."
                f"It should be in {self.supported_types}"
            )
        if age < 0:
            raise ValueError("Age needs to be positive")
        elif age <= 5:
            return getattr(self, f"{activity_type}_activity_babies_ids")
        elif age <= 11:
            return getattr(self, f"{activity_type}_activity_kids_ids")
        else:
            return getattr(self, f"{activity_type}_activity_ados_ids")



    def _compute_current_time(self):
        """
        Computes the current time.
        Odoo automatically handles timezone conversion for display.
        The value should be assigned in UTC.
        """
        now_utc = fields.Datetime.now()
        for record in self:
            tzinfo = timezone(record.timezone) if record.timezone else tools.utc
            record.center_current_time = now_utc.astimezone(tzinfo).strftime("%Y-%m-%d %H:%M:%S")

