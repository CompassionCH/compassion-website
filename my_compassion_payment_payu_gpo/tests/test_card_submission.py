from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.my_compassion.models.payment_transaction import (
    PaymentTransaction as My2PaymentTransaction,
)
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_payu_gpo.controllers.main import PayuGpoController
from odoo.addons.payment_payu_gpo.models.payment_transaction import (
    PaymentTransaction as PayuPaymentTransaction,
)
from odoo.addons.website.tools import MockRequest

from .common import PayuDigitalCase

CLIENT = "odoo.addons.payment_payu_gpo.payu_client.PayuClient"


@tagged("post_install", "-at_install")
class TestCardSubmission(PayuDigitalCase):
    """One card payment per MyCompassion order, checked when PayU's card
    route sends the card: two payment forms of the order may each have made
    a draft before."""

    def setUp(self):
        super().setUp()
        self.website = self.env.ref("my_compassion.my2_website")
        self.provider = self.env.ref("payment_payu_gpo.payment_provider_payu_gpo").copy(
            {"company_id": self.website.company_id.id}
        )
        self.provider.write(
            {
                "state": "test",
                "payu_gpo_pos_id": "300746",
                "payu_gpo_client_id": "300746",
                "payu_gpo_client_secret": "test-client-secret",
                "payu_gpo_second_key": "test-second-key",
            }
        )
        product = self.env["product.product"].create(
            {"name": "Card submission gift", "list_price": 50.0}
        )
        self.order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"]
                .create({"name": "Card Submission Donor", "email": "d@example.com"})
                .id,
                "website_id": self.website.id,
                "company_id": self.website.company_id.id,
                "order_line": [Command.create({"product_id": product.id})],
            }
        )

    def _draft(self, reference):
        """A card payment of the order, made by one of its payment forms."""
        return self.env["payment.transaction"].create(
            {
                "provider_id": self.provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_card").id,
                "partner_id": self.order.partner_id.id,
                "amount": self.order.amount_total,
                "currency_id": self.order.currency_id.id,
                "reference": reference,
                "operation": "online_direct",
                "sale_order_ids": [Command.set(self.order.ids)],
            }
        )

    def _send_card(self, tx):
        """The card route, as the payment form calls it with the Secure Form
        token."""
        with MockRequest(self.env):
            return PayuGpoController().payu_gpo_card_payment(
                tx.reference,
                payment_utils.generate_access_token(tx.reference),
                "TOK_CARD",
            )

    @contextmanager
    def _payu_takes_the_card_of(self, tx):
        """PayU accepts the card of tx, and its payment is pending. Yields
        the mock of the order creation."""
        with (
            patch(
                f"{CLIENT}.create_order",
                return_value={
                    "orderId": "PAYU-ORDER",
                    "status": {"statusCode": "SUCCESS"},
                },
            ) as create_order,
            patch(
                f"{CLIENT}.get_order",
                return_value={
                    "orders": [
                        {
                            "orderId": "PAYU-ORDER",
                            "extOrderId": tx.reference,
                            "status": "PENDING",
                        }
                    ]
                },
            ),
        ):
            yield create_order

    def test_one_card_reaches_payu_per_order(self):
        if not (
            hasattr(PayuPaymentTransaction, "_payu_gpo_check_card_submission")
            and hasattr(My2PaymentTransaction, "_my2_check_card_submission")
        ):
            self.skipTest(
                "needs payment_payu_gpo's _payu_gpo_check_card_submission and"
                " my_compassion's _my2_check_card_submission"
            )
        first = self._draft("payu-bridge-first-form")
        second = self._draft("payu-bridge-second-form")
        with self._payu_takes_the_card_of(first) as create_order:
            first_answer = self._send_card(first)
            second_answer = self._send_card(second)
        self.assertEqual(create_order.call_count, 1)
        self.assertNotIn("error", first_answer)
        self.assertEqual(first.state, "pending")
        self.assertEqual(
            second_answer["error"],
            "This donation is already paid, or its payment is under way.",
        )
        self.assertEqual(second.state, "cancel")

    def test_card_reaches_payu_without_the_order_check(self):
        """A my_compassion that does not check the card submission yet: the
        card route sends the card as usual."""
        if hasattr(My2PaymentTransaction, "_my2_check_card_submission"):
            self.skipTest("my_compassion checks the card submission")
        tx = self._draft("payu-bridge-only-form")
        with self._payu_takes_the_card_of(tx) as create_order:
            answer = self._send_card(tx)
        self.assertEqual(create_order.call_count, 1)
        self.assertNotIn("error", answer)
        self.assertEqual(tx.state, "pending")
