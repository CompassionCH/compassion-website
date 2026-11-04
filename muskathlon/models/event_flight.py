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
        # Each flight has its own task
        flights = super().create(vals_list)
        tasks = {
            "outbound": self.env.ref("muskathlon.task_flight_details"),
            "return": self.env.ref("muskathlon.task_return_flight"),
        }
        for flight in flights:
            task = tasks.get(flight.flight_type)
            flight.registration_id.task_ids.filtered(
                lambda t, task=task: t.task_id == task
            ).write({"done": True})
        return flights
