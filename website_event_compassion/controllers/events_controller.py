##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

import werkzeug

from odoo import _, fields, http
from odoo.http import Controller, request

from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.models.ir_http import sitemap_qs2dom

EVENTS_URL = "/events"


class EventsController(Controller):
    def sitemap_events(env, rule, qs):
        today = fields.Date.to_string(datetime.today())
        events = env["crm.event.compassion"]
        dom = sitemap_qs2dom(qs, EVENTS_URL, events._rec_name)
        dom += request.website.website_domain()
        dom += [("website_published", "=", True), ("end_date", ">=", today)]
        for reg in events.search(dom):
            loc = "/event/%s" % slug(reg)
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    def sitemap_participants(env, rule, qs):
        registrations = env["event.registration"]
        dom = sitemap_qs2dom(qs, "/event", registrations._rec_name)
        dom += request.website.website_domain()
        dom += [("website_published", "=", True)]
        for reg in registrations.search(dom):
            loc = f"/event/{slug(reg.compassion_event_id)}/{slug(reg)}"
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    @http.route("/events/", auth="public", website=True, sitemap=True)
    def list(self, **kwargs):
        today = fields.Date.to_string(datetime.today())
        # Events that are set to finish after today
        events_domain = [
            ("website_published", "=", True),
            ("end_date", ">=", today),
        ] + request.website.website_domain()
        started_events = request.env["crm.event.compassion"].search(
            events_domain, order="start_date asc", limit=10
        )
        if len(started_events) == 1:
            return request.redirect("/event/" + str(started_events.id))
        return request.render(
            "website_event_compassion.list", {"events": started_events}
        )

    ###################################################
    # Methods for the event page and event registration
    ###################################################
    @http.route(
        '/event/<model("crm.event.compassion"):event>/',
        auth="public",
        website=True,
        sitemap=sitemap_events,
    )
    def event_page(self, event, **kwargs):
        if not event.is_published and request.env.user.share:
            return request.redirect(EVENTS_URL)

        if not event.can_access_from_current_website() and request.env.user.share:
            raise werkzeug.exceptions.NotFound()

        values = self.get_event_page_values(event)
        return request.render("website_event_compassion.event_page", values)

    def get_event_page_values(self, event):
        """
        Processes the registration form and gets the values used by the website to
        render the event page.
        :param event: crm.event.compassion record to render
        :return: dict: values for the event website template
        """
        titles = request.env["res.partner.title"].sudo().search([])
        relation_types = (
            request.env["event.registration"]
            .sudo()
            .translate_selection_strings("emergency_relation_type")
        )
        return {
            "event": event,
            "start_date": event.get_date("start_date", "date_full"),
            "end_date": event.get_date("end_date", "date_full"),
            "additional_title": _("- Registration"),
            "titles": titles,
            "relation_types": relation_types,
            "main_object": event,
        }

    ###################################################
    # Methods for the participant page and the donation
    ###################################################
    @http.route(
        [
            "/event/<model('crm.event.compassion'):event>/<model("
            "'event.registration'):registration>/",
        ],
        auth="public",
        website=True,
        sitemap=sitemap_participants,
    )
    def participant_details(self, event, registration, **kwargs):
        """
        :param event: the event record
        :param reg_id: the registration record
        :return:the rendered page
        """
        if (
            not event.is_published
            or not registration.is_published
            or not registration.can_access_from_current_website()
        ):
            return request.redirect(EVENTS_URL)
        values = self.get_participant_page_values(event, registration)
        return request.render(values["website_template"], values)

    def get_participant_page_values(self, event, registration):
        """
        Gets the values used by the website to render the participant page.
        :param event: crm.event.compassion record to render
        :param kwargs: request arguments
        :return: dict: values for the event website template
        """
        return {
            "event": event,
            "registration": registration,
            "main_object": registration,
            "website_template": "website_event_compassion.participant_page",
        }

    @http.route(
        "/event/<model('crm.event.compassion'):event>/<model("
        "'event.registration'):registration>/donation/",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
    )
    def event_donation(self, event, registration, amount, **post):
        """
        Use the cart of the website to process the donation.
        Force the price of the order line to make sure it reflects the selected
        amount for donation.
        :param event: the event record
        :param registration: the registration record
        :param amount: the donation amount
        :param post: the post request
        :return: the rendered page
        """
        if not event.is_published:
            return request.redirect(EVENTS_URL)
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != "draft":
            request.session["sale_order_id"] = None
            sale_order = request.website.sale_get_order(force_create=True)
        product_id = event.odoo_event_id.donation_product_id.id
        order_line_id = sale_order._cart_update(
            product_id=product_id,
            set_qty=1,
        )["line_id"]
        order_line = request.env["sale.order.line"].sudo().browse(order_line_id)
        order_line.write(
            {
                "price_unit": amount,
                "registration_id": registration.id,
                "product_uom_qty": 1,
            }
        )
        order_line.order_id.workflow_process_id = request.env.ref(
            "sale_automatic_workflow.automatic_validation"
        ).sudo()
        return request.redirect("/shop/checkout?express=1")
