from datetime import datetime, timedelta
import math
from odoo import _, fields

from odoo.http import local_redirect, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal

# Avoids fetching too many donations in the portal
HISTORY_LIMIT = 1000


def _get_sponsorships(partner, state=None):
    """
    Find all the sponsorships of the given user.
    There is the possibility to fetch either only active sponsorships or only those
    that are terminated / cancelled. By default, all sponsorships are returned

    :return: a recordset of recurring.contract of the given user
    """

    def filter_sponsorships(sponsorship):
        can_show = True
        is_active = sponsorship.state not in ["draft", "cancelled", "terminated"]
        exit_communication_sent = (
                sponsorship.state == "terminated" and sponsorship.sds_state != "sub_waiting"
        )

        if state == "active":
            can_show = is_active or (
                    sponsorship.state == "terminated" and not exit_communication_sent
            )
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
        """
        The route to the donations and invoicing page
        :param invoice_page: index of the invoice pagination
        :param invoice_per_page: the number of invoices to display per page
        :param form_id: the id of the filled form or None
        :param kw: additional optional arguments
        :return: a redirection to a webpage
        """
        partner = request.env.user.partner_id

        invoice_search_criteria = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]

        move_obj = request.env["account.move"].sudo()
        # invoice to show for the given pagination index
        all_invoices = move_obj.read_group(
            invoice_search_criteria,
            ["amount_total"],
            ["last_payment:day"],
            orderby="last_payment desc",
            limit=HISTORY_LIMIT,
        )
        invoice_count = len(all_invoices)
        total_pages = math.ceil(invoice_count / invoice_per_page)
        next_page_url = f"/my2/donations/page/{invoice_page + 1}"
        previous_page_url = f"/my2/donations/page/{invoice_page - 1}"
        offset = (invoice_page - 1) * invoice_per_page
        invoices_per_day = all_invoices[offset: offset + invoice_per_page]

        for invoice_group in invoices_per_day:
            # Agrement data for displaying all invoices
            invoices = move_obj.search(invoice_group["__domain"])
            invoice_group["description"] = invoices.get_my_account_display_name()
            invoice_group["last_payment"] = invoices[0].get_date(
                "last_payment", "d MMM yyyy"
            )
            invoice_group["amount"] = (
                f"{int(invoice_group['amount_total']):,d} "
                f"{invoices[0].currency_id.name}"
            )

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

        active_sponsorships = _get_sponsorships(partner, state="active")
        currency = active_sponsorships.mapped("pricelist_id.currency_id")[:1].name

        # Dict of groups mapped to their sponsorships, and total amount
        # {group: (<sponsorships recordset>, total_amount string), ...}
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
        return request.render("my_compassion.my_account_donations_details", values)
