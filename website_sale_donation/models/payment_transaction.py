from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _send_donation_email(
        self, is_internal_notification=False, comment=None, recipient_email=None
    ):
        """We don't send emails for donation transactions."""
        pass
