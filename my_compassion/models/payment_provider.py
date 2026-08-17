from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    def _is_tokenization_required(self, my2_sponsorship=False, **kwargs):
        """Sponsorship first payments must save the instrument: the monthly
        off-session charge has nothing to charge without a token."""
        return my2_sponsorship or super()._is_tokenization_required(**kwargs)
