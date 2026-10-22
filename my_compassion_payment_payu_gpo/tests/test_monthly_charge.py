from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .common import PayuDigitalCase


@tagged("post_install", "-at_install")
class TestMonthlyCharge(PayuDigitalCase):
    """The monthly charge of a card saved at PayU. PayU tells its outcome
    later, by notification or when its status is read."""

    def setUp(self):
        super().setUp()
        self.contract, self.invoice, _token = self._make_payu_chargeable_invoice()
        self.handoffs = []
        patcher = patch.object(
            self.registry["recurring.contract"],
            "_on_digital_charge_failed",
            lambda contracts, invoice, reason: self.handoffs.append(
                (contracts, invoice, reason)
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _notify(self, tx, status, **order):
        """PayU's notification, or status read, of the order of tx."""
        return self.env["payment.transaction"]._handle_notification_data(
            "payu_gpo",
            {"order": {"extOrderId": tx.reference, "status": status, **order}},
        )

    def _bank_refuses_charges(self):
        """The refusal of a charge made with a saved card, as
        payment_payu_gpo records it: PayU cancels the order, and the
        transaction is in error."""
        transaction_class = self.registry["payment.transaction"]
        apply_order = transaction_class._payu_gpo_apply_order

        def apply(tx, notification_data):
            if (
                tx.operation == "offline"
                and notification_data["order"]["status"] == "CANCELED"
            ):
                tx._set_error("PayU: the bank refused the charge.")
            else:
                apply_order(tx, notification_data)

        return patch.object(transaction_class, "_payu_gpo_apply_order", apply)

    def test_refused_charge_starts_the_dunning_once(self):
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        self.assertEqual((tx.operation, tx.state), ("offline", "pending"))
        self.assertFalse(self.handoffs)
        with self._bank_refuses_charges():
            self._notify(tx, "CANCELED")
            self.assertEqual(tx.state, "error")
            self.assertEqual(
                self.handoffs, [(self.contract, self.invoice, tx.state_message)]
            )
            # PayU repeats its notifications
            self._notify(tx, "CANCELED")
        self.assertEqual(len(self.handoffs), 1)
        # the next daily run does not charge the card again
        self._run_charge_cron(lambda tx: tx._set_pending())
        self.assertEqual(self.invoice.transaction_ids, tx)

    def test_refusal_at_the_charge_is_handed_off_once(self):
        # PayU refuses the order at once: the charge hands it off, and the
        # notification that follows adds nothing.
        self._run_charge_cron(lambda tx: tx._set_error("PayU: declined"))
        tx = self.invoice.transaction_ids
        self.assertEqual(len(self.handoffs), 1)
        with self._bank_refuses_charges():
            self._notify(tx, "CANCELED")
        self.assertEqual(tx.state, "error")
        self.assertEqual(len(self.handoffs), 1)

    def test_sponsor_payment_error_is_no_failed_charge(self):
        # The sponsor pays on the site and sees the outcome there.
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": self.contract.payment_mode_id.payment_provider_id.id,
                "payment_method_id": self.env.ref("payment.payment_method_card").id,
                "partner_id": self.contract.partner_id.id,
                "amount": self.invoice.amount_residual,
                "currency_id": self.invoice.currency_id.id,
                "reference": "payu-bridge-sponsor-payment",
                "operation": "online_direct",
                "invoice_ids": [Command.set(self.invoice.ids)],
            }
        )
        tx._set_pending()
        # an order of another amount is refused
        self._notify(tx, "COMPLETED", totalAmount="1")
        self.assertEqual(tx.state, "error")
        self.assertFalse(self.handoffs)
