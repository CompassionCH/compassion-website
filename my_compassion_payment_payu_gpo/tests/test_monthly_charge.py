from contextlib import ExitStack
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .common import PayuDigitalCase

LOGGER = "odoo.addons.my_compassion_payment_payu_gpo.models.payment_transaction"


@tagged("post_install", "-at_install")
class TestMonthlyCharge(PayuDigitalCase):
    """The monthly charge of a card saved at PayU. PayU tells its outcome
    later, by notification or when its status is read."""

    def setUp(self):
        super().setUp()
        self.contract, self.invoice, _token = self._make_payu_chargeable_invoice()
        self.start_dunning = self.registry[
            "recurring.contract"
        ]._on_digital_charge_failed
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

    def test_rejected_notification_is_for_staff(self):
        # A notification about another amount or another order is rejected:
        # the charge is in error for staff to check, and the sponsor is not
        # asked to change a card that may have worked.
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        tx.provider_reference = "PAYU-ORDER-A"
        self._notify(tx, "CANCELED", orderId="PAYU-ORDER-B")
        self.assertEqual(tx.state, "error")
        self.assertFalse(self.handoffs)

    def test_notification_of_another_amount_is_for_staff(self):
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        self._notify(tx, "CANCELED", totalAmount="1")
        self.assertEqual(tx.state, "error")
        self.assertFalse(self.handoffs)

    def _refuse_with_a_failing_dunning(self, start_dunning, **patches):
        """PayU refuses the pending charge, and the dunning fails."""
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        contract_class = self.registry["recurring.contract"]
        patches["_on_digital_charge_failed"] = start_dunning
        with ExitStack() as stack:
            for name, method in patches.items():
                stack.enter_context(patch.object(contract_class, name, method))
            stack.enter_context(self._bank_refuses_charges())
            stack.enter_context(self.assertLogs(LOGGER, "ERROR"))
            self._notify(tx, "CANCELED")
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(tx.state, "error")
        # PayU delivers the notification again: nothing more happens
        with self._bank_refuses_charges():
            self._notify(tx, "CANCELED")
        self.assertEqual(tx.state, "error")
        return tx

    def test_refusal_is_kept_when_the_dunning_setup_fails(self):
        def no_configs(contracts):
            raise RuntimeError("The fix-it configuration cannot be read.")

        self._refuse_with_a_failing_dunning(
            self.start_dunning, _my2_fixit_configs=no_configs
        )

    def test_writes_of_a_failing_dunning_are_undone(self):
        def write_then_fail(contracts, invoice, reason):
            contracts.partner_id.comment = "Dunning started"
            raise RuntimeError("The dunning failed.")

        self._refuse_with_a_failing_dunning(write_then_fail)
        self.assertFalse(self.contract.partner_id.comment)

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
