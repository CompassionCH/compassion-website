import math
from datetime import datetime, timedelta

from odoo import fields
from odoo.http import request, route
from odoo.osv import expression

from odoo.addons.portal.controllers.portal import CustomerPortal


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

    @route(['/my2/my-donations', '/my2/my-donations/page/<int:invoice_page>'],
           type='http', auth="user", website=True)
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        """
        This is the original method for loading the full page.
        Its logic has been restored to its original state.
        """
        partner = request.env.user.partner_id
        values = self._prepare_portal_layout_values()
        move_obj = request.env["account.move"].sudo()

        invoice_search_criteria = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]
        offset = (invoice_page - 1) * invoice_per_page
        invoice_count = move_obj.search_count(invoice_search_criteria)
        total_pages = math.ceil(invoice_count / invoice_per_page)
        invoices_per_day = move_obj.read_group(
            invoice_search_criteria,
            ["amount_total"],
            ["last_payment:day"],
            orderby="last_payment desc",
            offset=offset,
            limit=invoice_per_page,
        )
        next_page_url = f"/my2/my-donations/page/{invoice_page + 1}"
        previous_page_url = f"/my2/my-donations/page/{invoice_page - 1}"

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
            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(g)
            sponsorships = active_sponsorships.filtered(lambda s, g=g: s.group_id == g)
            total = int(sum(sponsorships.mapped("total_amount")))

            sponsorships_by_group[g] = (sponsorships, f"{total:,d} {currency}")

        values = self._prepare_portal_layout_values()
        values.update(
            {
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


    @route('/my2/my-donations/history', type='json', auth="user", methods=['POST'],
           website=True)
    def my_donations_history(self, page=1, per_page=12, **kw):
        """
        This is the NEW route for AJAX calls.
        It now renders a specific part of the main page template.
        """
        partner = request.env.user.partner_id

        move_obj = request.env["account.move"].sudo()
        search_criteria = [
            ("partner_id", "=", partner.id), ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"), ("amount_total", "!=", 0),
        ]

        offset = (int(page) - 1) * per_page
        invoice_count = move_obj.search_count(search_criteria)
        total_pages = math.ceil(invoice_count / per_page)
        invoices_per_day = move_obj.read_group(
            search_criteria, ["amount_total"], ["last_payment:day"],
            orderby="last_payment desc", offset=offset, limit=per_page
        )
        all_domains = [g["__domain"] for g in invoices_per_day]
        if all_domains:
            combined_domain = expression.OR(all_domains)
            all_invoices_records = move_obj.search(combined_domain)

            def domain_key(domain):
                return tuple(sorted(map(tuple, domain)))

            invoices_by_domain = {domain_key(d): all_invoices_records.filtered_domain(d)
                                  for d in all_domains}

            for group in invoices_per_day:
                invoices = invoices_by_domain[domain_key(group["__domain"])]
                if invoices:
                    group["description"] = invoices.get_my_account_display_name()
                    group["last_payment"] = invoices[0].get_date("last_payment",
                                                                 "d MMM yyyy")
                    group[
                        "amount"] = f"{int(group['amount_total']):,d} {invoices[0].currency_id.name}"

                    invoices_by_domain = {}
                    for domain in all_domains:
                        key = domain_key(domain)
                        invoices_by_domain[key] = all_invoices_records.filtered_domain(
                            domain)


        history_data = {
            "invoices_per_day": invoices_per_day,
            "current_page": int(page),
            "total_pages": int(total_pages),
        }

        html = request.env['ir.qweb']._render(
            'my_compassion.my2_donations_history_content',
            values=history_data,
        )

        return {'html': html}