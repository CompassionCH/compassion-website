import math
from collections import defaultdict
from datetime import datetime, timedelta

from odoo import fields
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyDonationController(CustomerPortal):
    def _get_paid_invoices_filter(self, partner):
        paid_invoices_filter = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]
        return paid_invoices_filter

    def _get_paid_invoices_subset(self, partner, offset, amount):
        paid_invoices_subset = (
            request.env["account.move"]
            .sudo()
            .search(
                self._get_paid_invoices_filter(partner),
                offset=offset,
                limit=amount,
            )
        )
        return paid_invoices_subset

    def _get_paid_invoices_amount(self, partner):
        number_of_paid_invoices = (
            request.env["account.move"]
            .sudo()
            .search_count(self._get_paid_invoices_filter(partner))
        )
        return number_of_paid_invoices

    @route(
        ["/my2/my-donations"],
        type="http",
        auth="user",
        website=True,
    )
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Active sponsorships
        active_sponsorships = partner.get_portal_sponsorships("active")

        # Due invoices
        date_filter_up_bound = datetime.today() + timedelta(days=30)
        due_invoices = (
            request.env["account.move"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("payment_state", "=", "not_paid"),
                    ("invoice_category", "=", "sponsorship"),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("amount_total", "!=", 0),
                    ("invoice_date", "<", fields.Date.to_string(date_filter_up_bound)),
                ]
            )
        )

        # Computing the total price of the active sponsorships grouped per sponsorship frequency and payment method.
        # group_id groups the invoices that have the same payment method and frequency.
        tot_cost_per_frequency = defaultdict(lambda: defaultdict(float))

        for sponsorship in active_sponsorships:
            currency = sponsorship.pricelist_id.currency_id.name
            tot_cost_per_frequency[sponsorship.group_id.month_interval][
                currency
            ] += sponsorship.total_amount

        # redundant
        paid_invoices_offset = (invoice_page - 1) * invoice_per_page
        paid_invoices_subset = self._get_paid_invoices_subset(
            partner, paid_invoices_offset, invoice_per_page
        )
        total_paid_invoices = self._get_paid_invoices_amount(partner)
        total_pages = math.ceil(total_paid_invoices / invoice_per_page)

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "active_sponsorships": active_sponsorships,
                "tot_cost_per_frequency": tot_cost_per_frequency,
                "due_invoices": due_invoices,
                "paid_invoices_subset": paid_invoices_subset,
                "current_page": invoice_page,
                "total_pages": total_pages,
            }
        )
        return request.render("my_compassion.my2_my_donations_page", values)

    @route(
        "/my2/my-donations/history",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_donations_history(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Paid invoices
        paid_invoices_offset = (int(invoice_page) - 1) * invoice_per_page
        paid_invoices_subset = self._get_paid_invoices_subset(
            partner, paid_invoices_offset, invoice_per_page
        )

        # Paid invoices paging
        total_pages = (
            math.ceil(self._get_paid_invoices_amount(partner) / invoice_per_page)
            if invoice_per_page > 0
            else 0
        )

        history_data = {
            "current_page": int(invoice_page),
            "paid_invoices_subset": paid_invoices_subset,
            "total_pages": total_pages,
        }

        html = request.env["ir.qweb"]._render(
            "my_compassion.my2_donations_history_content",
            values=history_data,
        )

        return {"html": html}
