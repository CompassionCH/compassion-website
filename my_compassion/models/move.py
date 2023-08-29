##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "translatable.model"]

    gender = fields.Selection(store=False)

    def get_my_account_display_name(self):
        """
        Returns a nice name for displaying the given invoices in the portal.
        @return: string
        """
        children = self.mapped("invoice_line_ids.contract_id.child_id").sorted(
            "preferred_name"
        )
        children_names = children.get_list("preferred_name", 2, children.get_number())
        sponsorship_invoices = self.filtered(
            lambda i: i.invoice_category == "sponsorship"
        )
        gift_invoices = self.filtered(lambda i: i.invoice_category == "gift")
        if sponsorship_invoices:
            description = _("Sponsorship") + " " + children_names
            # Check if there are invoices for different months
            recurring_unit = sponsorship_invoices.mapped(
                "invoice_line_ids.contract_id.group_id"
            )[:1].recurring_unit
            occurrences = set()
            for inv_date in sponsorship_invoices.mapped("invoice_date"):
                occurrences.add(getattr(inv_date, recurring_unit))
            if len(occurrences) > 1:
                recurring_text = sponsorship_invoices.mapped(
                    "invoice_line_ids.contract_id.group_id"
                )[:1].translate("recurring_unit")
                description += f" ({len(sponsorship_invoices)} {recurring_text})"
        elif gift_invoices:
            description = _("Sponsorship gift") + " " + children_names
        else:
            description = self.get_list("invoice_line_ids.product_id.name")
        return description


class AccountInvoiceLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "translatable.model"]

    gender = fields.Selection(store=False)
