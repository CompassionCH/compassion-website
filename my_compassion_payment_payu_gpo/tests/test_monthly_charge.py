from contextlib import ExitStack
from unittest.mock import patch

from psycopg2.errors import SerializationFailure

from odoo import Command
from odoo.tests import tagged

from .common import PayuDigitalCase

LOGGER = "odoo.addons.my_compassion_payment_payu_gpo.models.payment_transaction"
CLIENT = "odoo.addons.payment_payu_gpo.payu_client.PayuClient"


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

    def test_refused_charge_starts_the_dunning_once(self):
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        self.assertEqual((tx.operation, tx.state), ("offline", "pending"))
        self.assertFalse(self.handoffs)
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

    def test_refusal_read_from_payu_starts_the_dunning_once(self):
        # The status read (cron, status page) finds the order PayU cancelled,
        # then PayU's notification of it arrives.
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        tx.provider_reference = "PAYU-ORDER-READ"
        cancelled = {
            "orders": [
                {
                    "orderId": "PAYU-ORDER-READ",
                    "extOrderId": tx.reference,
                    "status": "CANCELED",
                }
            ]
        }
        with patch(f"{CLIENT}.get_order", return_value=cancelled):
            tx._payu_gpo_refresh_from_api()
        self.assertEqual(tx.state, "error")
        self.assertEqual(len(self.handoffs), 1)
        self._notify(tx, "CANCELED", orderId="PAYU-ORDER-READ")
        self.assertEqual(len(self.handoffs), 1)
        # the next daily run does not charge the card again
        self._run_charge_cron(lambda tx: tx._set_pending())
        self.assertEqual(self.invoice.transaction_ids, tx)

    def test_notification_of_another_order_is_for_staff(self):
        # A notification that does not match the charge is held: the charge
        # stays pending for staff to check, and the sponsor is not asked to
        # change a card that may have worked.
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        tx.provider_reference = "PAYU-ORDER-A"
        self._notify(tx, "CANCELED", orderId="PAYU-ORDER-B")
        self.assertEqual(tx.state, "pending")
        self.assertFalse(self.handoffs)

    def test_notification_of_another_amount_is_for_staff(self):
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        self._notify(tx, "CANCELED", totalAmount="1")
        self.assertEqual(tx.state, "pending")
        self.assertFalse(self.handoffs)

    def test_charge_never_captured_is_no_card_failure(self):
        # Automatic collection is off on the PayU point of sale: PayU
        # authorized the charge, nobody captured it, and PayU cancelled it.
        # The card works: no request to change it.
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids
        self._notify(tx, "WAITING_FOR_CONFIRMATION")
        self.assertEqual(tx.state, "pending")
        self._notify(tx, "CANCELED")
        self.assertEqual(tx.state, "error")
        self.assertIn("never captured", tx.state_message)
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
            stack.enter_context(self.assertLogs(LOGGER, "ERROR"))
            self._notify(tx, "CANCELED")
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(tx.state, "error")
        # PayU delivers the notification again: nothing more happens
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
        self._notify(tx, "CANCELED")
        self.assertEqual(tx.state, "error")
        self.assertEqual(len(self.handoffs), 1)

    def test_concurrent_update_in_the_dunning_is_retried(self):
        # Odoo replays the whole notification on a concurrent update: it is
        # no failure for staff, and nothing may swallow it.
        self._run_charge_cron(lambda tx: tx._set_pending())
        tx = self.invoice.transaction_ids

        def conflict(contracts, invoice, reason):
            raise SerializationFailure("could not serialize access")

        with (
            patch.object(
                self.registry["recurring.contract"],
                "_on_digital_charge_failed",
                conflict,
            ),
            self.assertRaises(SerializationFailure),
        ):
            self._notify(tx, "CANCELED")

    def test_sponsor_payment_refusal_is_no_failed_charge(self):
        # The sponsor pays on the site and sees the refusal there: it is no
        # monthly charge to dun, even were PayU's module to record it as an
        # error (it cancels it).
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
        transaction_class = self.registry["payment.transaction"]
        with patch.object(
            transaction_class,
            "_payu_gpo_apply_order",
            lambda tx, notification_data: tx._set_error("PayU: refused."),
        ):
            self._notify(tx, "CANCELED")
        self.assertEqual(tx.state, "error")
        self.assertFalse(self.handoffs)
