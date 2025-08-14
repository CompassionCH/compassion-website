import math
from datetime import datetime, timedelta

from odoo import fields
from odoo.http import request, route
from odoo.osv import expression

from odoo.addons.portal.controllers.portal import CustomerPortal

# Prevents fetching too many records in the portal.
HISTORY_LIMIT = 300


def _get_sponsorships(partner, state=None):
    """Finds all sponsorships for a partner, with custom state filtering."""

    def filter_sponsorships(sponsorship):
        can_show = True
        is_active = sponsorship.state not in ["draft", "cancelled", "terminated"]
        exit_communication_sent = (
            sponsorship.state == "terminated" and sponsorship.sds_state != "sub_waiting"
        )

        # 'active' includes sponsorships pending final communication.
        if state == "active":
            can_show = is_active or (
                sponsorship.state == "terminated" and not exit_communication_sent
            )
        # 'terminated' only shows sponsorships after final communication is sent.
        elif state == "terminated":
            can_show = exit_communication_sent
        elif state == "write":
            can_show = sponsorship.can_write_letter

        return can_show

    return (
        partner.get_portal_sponsorships()
        .with_context(allow_during_suspension=True)
        .filtered(filter_sponsorships)
    )


class MyDonationController(CustomerPortal):
    @route(
        [
            "/my2/my-donations",
            "/my2/my-donations/page/<int:invoice_page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        """Renders the 'My Donations' portal page with invoices and sponsorships."""
        partner = request.env.user.partner_id

        invoice_search_criteria = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]

        move_obj = request.env["account.move"].sudo()
        # Group paid invoices by day for display and pagination.
        all_invoices = move_obj.read_group(
            invoice_search_criteria,
            ["amount_total"],
            ["last_payment:day"],
            orderby="last_payment desc",
            limit=HISTORY_LIMIT,
        )
        invoice_count = len(all_invoices)
        total_pages = math.ceil(invoice_count / invoice_per_page)
        next_page_url = f"/my2/my-donations/page/{invoice_page + 1}"
        previous_page_url = f"/my2/my-donations/page/{invoice_page - 1}"
        offset = (invoice_page - 1) * invoice_per_page
        invoices_per_day = all_invoices[offset : offset + invoice_per_page]

        # Fetch all invoice records for the current page in a single search.
        all_domains = [g["__domain"] for g in invoices_per_day]
        combined_domain = expression.OR(all_domains)
        all_invoices_records = move_obj.search(combined_domain)

        # Helper to map the fetched records back to their original groups.
        def domain_key(domain):
            return tuple(sorted(map(tuple, domain)))

        invoices_by_domain = {}
        for domain in all_domains:
            key = domain_key(domain)
            invoices_by_domain[key] = all_invoices_records.filtered_domain(domain)

        # Populate display data for each invoice group.
        for invoice_group in invoices_per_day:
            invoices = invoices_by_domain[domain_key(invoice_group["__domain"])]
            if invoices:
                invoice_group["description"] = invoices.get_my_account_display_name()
                invoice_group["last_payment"] = invoices[0].get_date(
                    "last_payment", "d MMM yyyy"
                )
                invoice_group["amount"] = (
                    f"{int(invoice_group['amount_total']):,d} "
                    f"{invoices[0].currency_id.name}"
                )

        # Fetch outstanding invoices that are due within 30 days.
        in_one_month = datetime.today() + timedelta(days=30)
        due_invoices = move_obj.search(
            [
                ("partner_id", "=", partner.id),
                ("payment_state", "=", "not_paid"),
                ("invoice_category", "=", "sponsorship"),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("amount_total", "!=", 0),
                ("invoice_date", "<", fields.Date.to_string(in_one_month)),
            ]
        )

        # Fetch and group active sponsorships for display.
        active_sponsorships = _get_sponsorships(partner, state="active")
        currency = (
            (active_sponsorships.mapped("pricelist_id.currency_id")[:1]).name or ""
        )

        sponsorships_by_group = {}
        for g in active_sponsorships.mapped("group_id"):
            sponsorships = active_sponsorships.filtered(lambda s, g=g: s.group_id == g)
            total = int(sum(sponsorships.mapped("total_amount")))
            sponsorships_by_group[g] = (sponsorships, f"{total:,d} {currency}")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "partner": partner,
                "sponsorships_by_group": sponsorships_by_group,
                "invoices_per_day": invoices_per_day,
                "current_page": invoice_page,
                "total_pages": total_pages,
                "next_page_url": next_page_url,
                "previous_page_url": previous_page_url,
                "due_invoices": due_invoices,
            }
        )
        return request.render("my_compassion.my2_my_donations_page", values)
