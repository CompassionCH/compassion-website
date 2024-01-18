##############################################################################
#
#    Copyright (C) 2019 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models


class EventFlight(models.Model):
    _name = "event.flight"
    _inherit = "translatable.model"
    _description = "Event participant flight"
    _rec_name = "flight_number"
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

    _sql_constraints = [
        (
            "flight_unique",
            "unique (registration_id, flight_type)",
            "A participant can have only one flight of each type.",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # If the flight already exists, update its information automatically.
        res = self.env["event.flight"]
        for vals in vals_list:
            existing_flight = self.search(
                [
                    ("registration_id", "=", vals["registration_id"]),
                    ("flight_type", "=", vals["flight_type"]),
                ]
            )
            if existing_flight:
                existing_flight.write(vals)
                res += existing_flight
            else:
                res += super().create(vals)
        return res
