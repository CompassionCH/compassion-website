from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    def _is_tokenization_required(self, my2_sponsorship=False, **kwargs):
        """Sponsorship first payments must save the instrument: the monthly
        off-session charge has nothing to charge without a token.

        The flag arrives as a kwarg when the transaction is created and as
        a context key when the payment form is rendered. The provider's own
        inline form template calls this method with its fixed kwargs and
        feeds the answer to its payment widget, so only the environment can
        carry the flag at render time.
        """
        return bool(
            my2_sponsorship
            or self.env.context.get("my2_sponsorship")
            or super()._is_tokenization_required(**kwargs)
        )
