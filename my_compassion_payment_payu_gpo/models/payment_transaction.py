##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _payu_gpo_card_is_recurring(self):
        """A card saved for contract groups pays their monthly contributions:
        scheduled recurring charges, registered as such at PayU and the bank.

        These are the cards _my2_save_token_on_groups puts on the groups: of a
        digital sponsorship's invoices, or of the update-card page.
        """
        return bool(
            self.my2_card_update_group_id
            or self.invoice_ids.filtered(
                "line_ids.contract_id.group_id.payment_mode_id.payment_provider_id"
            )
            or super()._payu_gpo_card_is_recurring()
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
