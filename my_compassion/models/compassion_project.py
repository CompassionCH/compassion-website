##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class CompassionProject(models.Model):
    _inherit = "compassion.project"

    supported_types = ["cognitive", "physical", "socio", "spiritual"]

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
