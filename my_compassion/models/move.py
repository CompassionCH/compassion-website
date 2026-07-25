##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "translatable.model"]

    gender = fields.Selection(
        [
            ("M", "Male"),
            ("F", "Female"),
        ],
        store=False,
    )
    my2_can_charge_digital = fields.Boolean(
        compute="_compute_my2_can_charge_digital",
        help="The invoice can be charged off-session against the saved"
        " payment instrument of its contract group.",
    )

    @api.depends(
        "state",
        "payment_state",
        "payment_mode_id.payment_provider_id",
        "line_ids.contract_id.group_id.payment_token_id",
        "transaction_ids.state",
    )
    def _compute_my2_can_charge_digital(self):
        for move in self:
            # invoice staff are not payment.provider/token admins: read
            # those records elevated, the compute only exposes a boolean
            move_sudo = move.sudo()
            open_tx = move_sudo.transaction_ids.filtered(
                lambda t: t.state in ("pending", "authorized", "done")
            )
            move.my2_can_charge_digital = bool(
                move.move_type == "out_invoice"
                and move.state == "posted"
                and move.payment_state in ("not_paid", "partial")
                and move_sudo.payment_mode_id.payment_provider_id
                and move_sudo.line_ids.contract_id.group_id.payment_token_id
                and not open_tx
            )

    def _my2_serialize_charge_attempts(self):
        """Serialize concurrent charge attempts on these invoices.

        Odoo runs at repeatable read: two transactions charging the same
        invoice (nightly cron, staff button, update-card page) would each
        pass the open-transaction guard against their own snapshot and
        both send a real charge. The no-op update creates a new row
        version, so the concurrent loser fails with a serialization error
        and Odoo retries it against the committed winner, whose
        transaction then closes the guard.
        """
        if self.ids:
            self.env.cr.execute(
                "UPDATE account_move SET write_date = write_date" " WHERE id IN %s",
                [tuple(self.ids)],
            )

    def action_charge_digital_invoice(self):
        """Staff fallback: charge the saved card now.

        This is the manual retry path when an automatic off-session charge
        failed definitively (the cron never re-charges an invoice whose
        attempt was consumed).
        """
        self.ensure_one()
        # The view only hides the button from other groups. The RPC endpoint
        # stays reachable by any logged in user, so the caller rights are
        # checked here before anything is charged.
        self.check_access("write")
        # The charge path reads provider and token records that invoice staff
        # cannot access. The charge amount and target come from the invoice
        # itself, never from the caller.
        tx = (
            self.env["recurring.contract.group"]
            .sudo()
            ._charge_digital_invoice(self.sudo(), force=True)
        )
        if tx is None:
            raise UserError(
                _(
                    "This invoice cannot be charged: a payment is already"
                    " open or done, or no valid saved card is available."
                )
            )
        if tx.state == "done":
            message, message_type = _("The payment succeeded."), "success"
        elif tx.state == "pending":
            message, message_type = (
                _(
                    "The payment was refused; the provider scheduled"
                    " automatic retries."
                ),
                "info",
            )
        else:
            # the transaction record keeps the failure; raising here would
            # roll it back
            message, message_type = (
                _("The payment failed: %s", tx.state_message),
                "danger",
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": message_type},
        }

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

    gender = fields.Selection(
        [
            ("M", "Male"),
            ("F", "Female"),
        ],
        store=False,
    )
