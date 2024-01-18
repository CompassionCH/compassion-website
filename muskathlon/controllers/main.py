##############################################################################
#
#    Copyright (C) 2018-2021 Compassion CH (http://www.compassion.ch)
#    @author: Sebastien Toth <popod@me.com>, Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request, route

from odoo.addons.website_event_compassion.controllers.events_controller import (
    EventsController,
)


class MuskathlonWebsite(EventsController):
    def get_event_page_values(self, event):
        result = super().get_event_page_values(event)
        result.update(
            {
                "sport_disciplines": event.sport_discipline_ids,
            }
        )
        return result

    @route(
        [
            "/my/events/<model('event.registration'):registration>/fundraising",
        ],
        auth="user",
        website=True,
        sitemap=False,
    )
    def muskathlon_order_material(self, registration, form_id=None, **kw):
        flyer = "/muskathlon/static/src/img/muskathlon_parrain_example_"
        flyer += request.env.lang[:2] + ".jpg"
        staff_id = request.env["res.config.settings"].get_param(
            "muskathlon_order_notify_id"
        )
        values = {
            "main_object": registration,
            "flyer_image": flyer,
            "staff_id": staff_id,
        }
        return request.render("muskathlon.my_muskathlon_order_material", values)
