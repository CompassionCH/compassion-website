from odoo.tests import tagged

from ..models.payment_transaction import PaymentTransaction as BridgeTransaction
from .common import PayuDigitalCase


@tagged("post_install", "-at_install")
class TestPaymentOutcome(PayuDigitalCase):
    def test_unconfirmed_payment_is_no_certain_refusal(self):
        # what the bridge's override calls with super()
        below_the_bridge = super(
            BridgeTransaction, self.registry["payment.transaction"]
        )
        if not hasattr(below_the_bridge, "_my2_refusal_is_certain"):
            self.skipTest("needs my_compassion's _my2_refusal_is_certain")
        contract, invoice, _token = self._make_payu_chargeable_invoice()
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": contract.payment_mode_id.payment_provider_id.id,
                "payment_method_id": self.env.ref("payment.payment_method_card").id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "payu-bridge-unconfirmed",
                "operation": "online_direct",
            }
        )
        tx._set_error("PayU: the bank refused the payment.")
        self.assertTrue(tx._my2_refusal_is_certain())
        tx.payu_gpo_unconfirmed = True
        self.assertFalse(tx._my2_refusal_is_certain())
