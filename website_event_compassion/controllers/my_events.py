from odoo.http import request, route
from odoo.tools.misc import format_date

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyEventsController(CustomerPortal):
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

    @route("/my/events/tasks/<model('event.registration.task.rel'):task>")
    def task_click(self, task, **kwargs):
        if task.task_id.task_complete_on_click:
            task.done = True
        if task.task_url:
            return request.redirect(task.task_url)
        else:
            slug = request.env["ir.http"]._slug
            return request.redirect(f"/my/events/{slug(task.registration_id)}/")
