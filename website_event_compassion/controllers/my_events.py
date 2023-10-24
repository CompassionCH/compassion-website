from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyEventsController(CustomerPortal):
    @route("/my/events/", auth="user", website=True)
    def my_events(self, **kwargs):
        values = self._prepare_portal_layout_values()
        values["registrations"] = request.env["event.registration"].search(
            [
                ("partner_id", "=", request.env.user.partner_id.id),
                ("state", "in", ("open", "done")),
            ]
        )
        return request.render("website_event_compassion.my_events_list", values)

    @route(
        "/my/events/<model('event.registration'):registration>/",
        auth="user",
        website=True,
    )
    def my_registration(self, registration, **kwargs):
        values = self._prepare_portal_layout_values()
        values["registration"] = registration
        values["donations"] = self.get_donations(registration)
        return request.render("website_event_compassion.my_event_details", values)

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
                ]
            )
        )
        for move_line in donation_move_lines:
            donations.append(
                {
                    "date_str": move_line.get_date("date"),
                    "date": move_line.date,
                    "amount": str(move_line.price_total),
                    "currency": move_line.currency_id.symbol,
                    "donor": move_line.partner_id.preferred_name,
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
                    "donor": sponsorship.partner_id.preferred_name,
                }
            )
        donations.sort(key=lambda x: x["date"], reverse=True)
        return donations
