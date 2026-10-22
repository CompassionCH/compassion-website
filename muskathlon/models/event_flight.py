##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, models


class EventFlight(models.Model):
    _inherit = "event.flight"

    @api.model_create_multi
    def create(self, vals_list):
        # Check if all flights are entered
        flights = super().create(vals_list)
        task_flight = self.env.ref("muskathlon.task_flight_details")
        for registration in flights.mapped("registration_id"):
            if len(registration.flight_ids) == 2:
                registration.task_ids.filtered(
                    lambda t: t.task_id == task_flight
                ).write({"done": True})
        return flights
