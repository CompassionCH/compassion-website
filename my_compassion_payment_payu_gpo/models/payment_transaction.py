##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import models

from odoo.addons.payment_payu_gpo import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _payu_gpo_card_is_recurring(self):
        """A card that becomes the card of contract groups pays their monthly
        contributions: scheduled recurring charges, registered as such at
        PayU and the bank. Any other saved card stays a card on file.
        """
        return bool(
            self._my2_groups_taking_the_token() or super()._payu_gpo_card_is_recurring()
        )

    def _process_notification_data(self, notification_data):
        """A refused monthly charge reaches the contracts' dunning once.

        PayU answers a charge of a saved card only later, by notification
        or status read, both handled here: _charge_digital_invoice has long
        returned by then. PayU refuses a charge by cancelling its order, and
        repeats its notifications: only the one that moves the charge to
        error counts. A notification rejected as being about another order
        or amount also errors the charge, which is for staff to check.
        """
        order = notification_data.get("order") or {}
        refused = (
            self.provider_code == const.PROVIDER_CODE
            and self.operation == "offline"
            and self.state != "error"
            and order.get("status") in const.STATUS_MAPPING["canceled"]
            and not self._payu_gpo_mismatch(
                order, order.get("orderId"), self.amount, amount_key="totalAmount"
            )
        )
        res = super()._process_notification_data(notification_data)
        if refused and self.state == "error":
            for invoice in self.invoice_ids.filtered(
                "line_ids.contract_id.group_id.payment_mode_id.payment_provider_id"
            ):
                self._my2_start_dunning(invoice)
        return res

    def _my2_start_dunning(self, invoice):
        """Hand the refused charge of invoice to its contracts' dunning.

        A failure there must never undo the refusal: PayU would deliver the
        notification again, into the same failure.
        """
        try:
            with self.env.cr.savepoint():
                invoice.line_ids.contract_id._on_digital_charge_failed(
                    invoice, self.state_message
                )
        except Exception:
            _logger.exception(
                "Could not start the dunning of invoice %s after PayU refused"
                " the charge %s. Staff must tell the sponsor.",
                invoice.name,
                self.reference,
            )

    def _payu_gpo_buyer_names(self):
        """A payer known by email only (fast checkout, visitor donation) has
        the placeholder name, which PayU would show on its payment page: no
        name is sent, and PayU asks it. The name on the card, once typed, is
        sent as usual."""
        if (
            not self.payu_gpo_cardholder_name
            and self.partner_id.sudo().my2_name_placeholder
        ):
            return "", ""
        return super()._payu_gpo_buyer_names()

    def _my2_cardholder_name_payu_gpo(self, notification_data):
        """The payer's name for my_compassion's placeholder replacement.

        PayU reports no cardholder name of its own. The name on the card typed
        next to the Secure Form is kept on the transaction, and sent to PayU as
        the buyer, which PayU echoes back. A payment without it (BLIK, bank
        transfer) sends no buyer name for a placeholder payer, and the echo
        then carries whatever PayU asked, if anything: the thank-you page or
        the details form asks otherwise.
        """
        if self.payu_gpo_cardholder_name:
            return self.payu_gpo_cardholder_name
        buyer = (notification_data.get("order") or {}).get("buyer")
        if not isinstance(buyer, dict):
            return ""
        name = " ".join(
            part.strip()
            for part in (buyer.get("firstName"), buyer.get("lastName"))
            if isinstance(part, str) and part.strip()
        )
        if name == self.env["res.partner"].MY2_PLACEHOLDER_NAME:
            return ""
        return name

    def _my2_refusal_is_certain(self):
        """A payment PayU never confirmed may have been made: its error is
        no refusal."""
        return not self.payu_gpo_unconfirmed and super()._my2_refusal_is_certain()
