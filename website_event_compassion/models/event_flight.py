##############################################################################
#
#    Copyright (C) 2019 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, models


class EventFlight(models.Model):
    _name = "event.flight"
    _inherit = "translatable.model"
    _description = "Event participant flight"
    _rec_name = "flight_number"
    # A journey may have connections: a participant gives several flights of
    # each type, shown in the order of their departure.
    _order = "departure asc"

    registration_id = fields.Many2one(
        "event.registration", "Participant", required=True, readonly=False, index=True
    )
    flight_type = fields.Selection(
        [
            ("outbound", "Outbound flight"),
            ("return", "Return flight"),
        ]
    )
    flying_company = fields.Char()
    flight_number = fields.Char(required=True, index=True)
    departure = fields.Datetime(required=True)
    arrival = fields.Datetime(required=True)
