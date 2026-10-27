import json

from werkzeug.exceptions import NotFound

from odoo.exceptions import ValidationError
from odoo.http import request, route
from odoo.tools.misc import format_date

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website.controllers.form import WebsiteForm

# The participant forms of /my/events (T3572). They post here instead of to
# the generic /website/form, which would take any registration_id.
OWNER_FORMS = {
    "registration_edit": "event.registration.form",
    "flight": "event.flight",
}

# Confidential documents of a participant, with the staff group that may
# read them besides the participant.
DOCUMENT_GROUPS = {
    "passport": "event.group_event_user",
    "criminal_record": "child_protection.group_criminal_record",
}


def _owned_registration(registration_id):
    """The registration of the logged-in participant, or 404.

    Checked before anything is done with elevated rights: the id comes from
    the browser, and a registration of someone else must not tell itself
    apart from one that does not exist.
    """
    try:
        registration_id = int(registration_id)
    except (TypeError, ValueError) as error:
        raise NotFound() from error
    registration = (
        request.env["event.registration"].sudo().browse(registration_id).exists()
    )
    if not registration or registration.partner_id != request.env.user.partner_id:
        raise NotFound()
    return registration


class MyEventsController(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        events_domain = [
            ("partner_id", "=", request.env.user.partner_id.id),
            ("state", "!=", "cancel"),
        ]
        if not counters:
            events = request.env["event.registration"].search(events_domain, limit=2)
            values["my_events_url"] = "/my/events" + (
                f"/{events.id}" if len(events) == 1 else ""
            )

        if "event_tasks_count" in counters:
            values["event_tasks_count"] = request.env[
                "event.registration.task.rel"
            ].search_count(
                [
                    ("registration_id.partner_id", "=", request.env.user.partner_id.id),
                    ("done", "=", False),
                    ("task_id.website_published", "=", True),
                ]
            )
        if "events_count" in counters:
            values["events_count"] = request.env["event.registration"].search_count(
                events_domain
            )
        return values

    @route("/my/events/", auth="user", website=True)
    def my_events(self, **kwargs):
        values = self._prepare_portal_layout_values()
        values["registrations"] = request.env["event.registration"].search(
            [
                ("partner_id", "=", request.env.user.partner_id.id),
                ("state", "!=", "cancel"),
            ]
        )
        return request.render("website_event_compassion.my_events_list", values)

    @route(
        [
            "/my/events/<model('event.registration'):registration>/",
            "/my/events/<model('event.registration'):registration>/<string:edit_mode>",
        ],
        auth="user",
        website=True,
    )
    def my_registration(self, registration, edit_mode=False, **kwargs):
        if (
            request.env.user.partner_id.id == registration.partner_id.id
            or request.env.user.has_group("base.group_system")
        ):
            values = self._prepare_portal_layout_values()
            values.update(
                {
                    "registration": registration,
                    "donations": self.get_donations(registration),
                    "edit_mode": edit_mode,
                }
            )
            return request.render("website_event_compassion.my_event_details", values)
        else:
            return request.redirect("/my/events")

    def get_donations(self, registration):
        partner = registration.partner_id
        event = registration.compassion_event_id
        donations = []
        donation_move_lines = (
            request.env["account.move.line"]
            .sudo()
            .search(
                [
                    ("user_id", "=", partner.id),
                    ("payment_state", "=", "paid"),
                    ("event_id", "=", event.id),
                    ("move_id.invoice_category", "=", "fund"),
                ]
            )
        )
        for move_line in donation_move_lines:
            donations.append(
                {
                    "date_str": format_date(request.env, move_line.date),
                    "date": move_line.date,
                    "amount": str(move_line.price_total),
                    "currency": move_line.currency_id.symbol,
                    "donor firstname": move_line.partner_id.preferred_name or "",
                    "donor lastname": move_line.partner_id.lastname
                    if move_line.partner_id.preferred_name
                    != move_line.partner_id.lastname
                    else "",
                    "donor email": move_line.partner_id.email or "",
                }
            )
        donation_sponsorships = (
            request.env["recurring.contract"]
            .sudo()
            .search(
                [
                    ("ambassador_id", "=", partner.id),
                    ("origin_id.event_id", "=", event.id),
                    ("state", "!=", "cancelled"),
                ]
            )
        )
        for sponsorship in donation_sponsorships:
            donations.append(
                {
                    "date_str": sponsorship.get_date("create_date"),
                    "date": sponsorship.create_date.date(),
                    "amount": str(registration.event_id.sponsorship_donation_value),
                    "currency": event.currency_id.symbol,
                    "donor firstname": sponsorship.partner_id.preferred_name or "",
                    "donor lastname": sponsorship.partner_id.lastname
                    if sponsorship.partner_id.preferred_name
                    != sponsorship.partner_id.lastname
                    else "",
                    "donor email": sponsorship.partner_id.email or "",
                }
            )
        donations.sort(key=lambda x: x["date"], reverse=True)
        return donations

    @route(
        "/my/events/tasks/<model('event.registration.task.rel'):task>",
        auth="user",
        website=True,
    )
    def task_click(self, task, **kwargs):
        if task.registration_id.partner_id != request.env.user.partner_id:
            raise NotFound()
        if task.task_id.task_complete_on_click:
            task.sudo().done = True
        if task.task_url:
            return request.redirect(task.task_url)
        else:
            slug = request.env["ir.http"]._slug
            return request.redirect(f"/my/events/{slug(task.registration_id)}/")

    @route(
        "/my/events/<int:registration_id>/document/<string:document>",
        auth="user",
        website=True,
    )
    def registration_document(self, registration_id, document, **kwargs):
        """A confidential document of a participant: for the participant
        and for the staff of its group, nobody else."""
        group = DOCUMENT_GROUPS.get(document)
        if not group:
            raise NotFound()
        registration = (
            request.env["event.registration"].sudo().browse(registration_id).exists()
        )
        if not registration or not (
            registration.partner_id == request.env.user.partner_id
            or request.env.user.has_group(group)
        ):
            raise NotFound()
        if not registration[document]:
            raise NotFound()
        filename = f"{document}_{registration.partner_id.name}"
        return (
            request.env["ir.binary"]
            ._get_stream_from(registration, document, filename=filename)
            .get_response(as_attachment=True)
        )


class MyEventsFormController(WebsiteForm):
    @route(
        "/my/events/form/<string:form>",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_event_form(self, form, **kwargs):
        """The participant forms of /my/events, for their own registration
        only. Same answer as /website/form, which the form script expects."""
        model_name = OWNER_FORMS.get(form)
        if not model_name:
            raise NotFound()
        registration = _owned_registration(kwargs.get("registration_id"))
        model = request.env["ir.model"].sudo()._get(model_name)
        try:
            values = self.extract_data(model, kwargs)["record"]
        except ValidationError as e:
            return json.dumps({"error_fields": e.args[0]})
        values["registration_id"] = registration.id
        if model_name == "event.flight":
            record = self._save_flight(registration, values)
        else:
            record = request.env[model_name].sudo().create(values)
        return json.dumps({"id": record.id})

    def _save_flight(self, registration, values):
        """A participant has one flight of each type: entering it again
        corrects it."""
        flight_types = dict(
            request.env["event.flight"]._fields["flight_type"].selection
        )
        if values.get("flight_type") not in flight_types:
            raise NotFound()
        flight = registration.flight_ids.filtered(
            lambda f: f.flight_type == values["flight_type"]
        )
        if flight:
            flight.write(values)
            return flight
        return request.env["event.flight"].sudo().create(values)
