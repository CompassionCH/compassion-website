import math
from datetime import datetime, timedelta

from odoo import fields
from odoo.http import request, route
from odoo.osv import expression

from odoo.addons.portal.controllers.portal import CustomerPortal

class MyDonationController(CustomerPortal):
    def get_paid_invoices_filter(self, partner):
        paid_invoices_filter = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]
        return paid_invoices_filter

    def get_paid_invoices_subset(self, partner, offset, amount):
        paid_invoices_subset = request.env["account.move"].sudo().search(
            self.get_paid_invoices_filter(partner),
            offset=offset,
            limit=amount,
        )
        return paid_invoices_subset

    def get_paid_invoices_amount(self, partner):
        number_of_paid_invoices = request.env["account.move"].sudo().search_count(
            self.get_paid_invoices_filter(partner)
        )
        return number_of_paid_invoices

    @route(['/my2/my-donations', '/my2/my-donations/page/<int:invoice_page>'],
           type='http', auth="user", website=True)
    def my_donations(self,invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Active sponsorships
        active_sponsorships = partner.get_portal_sponsorships("active")

        # Due invoices
        date_filter_up_bound = datetime.today() + timedelta(days=30)
        due_invoices = request.env["account.move"].sudo().search([
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "not_paid"),
            ("invoice_category", "=", "sponsorship"),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("amount_total", "!=", 0),
            ("invoice_date", "<", fields.Date.to_string(date_filter_up_bound)),
        ])

        # Computing the total price of the active sponsorships grouped per sponsorship frequency and payment method.
        # group_id groups the invoices that have the same payment method and frequency.
        grouped_sponsorships = active_sponsorships.mapped("group_id")
        tot_cost_per_frequency = {}
        for group in grouped_sponsorships:
            group_price = group.total_amount
            group_frequency = group.month_interval
            # Here I'm assuming that every entry in the group has the same payment method
            group_currency =  (active_sponsorships.mapped("pricelist_id.currency_id")[:1]).name or ""
            tot_cost_per_frequency[group_frequency] = (group_price, group_currency)

        # redundant
        paid_invoices_offset = (invoice_page - 1) * invoice_per_page
        paid_invoices_subset = self.get_paid_invoices_subset(
            partner,
            paid_invoices_offset,
            invoice_per_page
        )
        total_paid_invoices = self.get_paid_invoices_amount(partner)
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

    @route('/my2/my-donations/history', type='json', auth="user", methods=['POST'],
           website=True)
    def my_donations_history(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Paid invoices
        paid_invoices_offset = (int(invoice_page) - 1) * invoice_per_page
        paid_invoices_subset = self.get_paid_invoices_subset(partner,
                                                             paid_invoices_offset,
                                                             invoice_per_page)

        # Paid invoices paging
        total_pages = math.ceil(
            self.get_paid_invoices_amount(partner) / invoice_per_page)

        history_data = {
            "current_page": int(invoice_page),
            "paid_invoices_subset": paid_invoices_subset,
            "total_pages": total_pages,
        }

        html = request.env['ir.qweb']._render(
            'my_compassion.my2_donations_history_content',
            values=history_data,
        )

        return {'html': html}