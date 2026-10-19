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
