##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Quentin Gigon
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, fields, models


class EventCompassion(models.Model):
    """A Compassion event."""

    _inherit = "crm.event.compassion"

    crowdfunding_project_id = fields.Many2one(
        "crowdfunding.project", "Crowdfunding project", ondelete="cascade"
    )

    def get_event_types(self):
        res = super().get_event_types()
        res.append(("crowdfunding", _("Crowdfunding")))
        return res
