from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestDigitalSeam(DigitalSeamCase):
    def test_find_or_create_group_is_idempotent(self):
        Group = self.env["recurring.contract.group"]
        g1 = Group._find_or_create_group(self.partner, self.company, self.mode)
        g2 = Group._find_or_create_group(self.partner, self.company, self.mode)
        self.assertEqual(g1, g2)
        self.assertEqual(g1.partner_id, self.partner)
        self.assertEqual(g1.company_id, self.company)
        self.assertEqual(g1.payment_mode_id, self.mode)

    def test_find_or_create_group_modeless(self):
        Group = self.env["recurring.contract.group"]
        empty_mode = self.env["account.payment.mode"]
        g = Group._find_or_create_group(self.partner, self.company, empty_mode)
        self.assertFalse(g.payment_mode_id)
        self.assertEqual(g.company_id, self.company)
        # mode-less and mode-ful groups are distinct
        g_mode = Group._find_or_create_group(self.partner, self.company, self.mode)
        self.assertNotEqual(g, g_mode)

    def test_token_company_constraint(self):
        other_company = self.env["res.company"].create(
            {"name": "Digital Seam Other Co"}
        )
        provider = self.env["payment.provider"].create(
            {
                "name": "Digital Seam Provider",
                "code": "none",
                "company_id": other_company.id,
            }
        )
        psp_method = self.env["payment.method"].search([], limit=1)
        token = self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": psp_method.id,
                "partner_id": self.partner.id,
                "provider_ref": "digital-seam-test-ref",
                "payment_details": "1234",
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            self.partner, self.company, self.mode
        )
        # token belongs to other_company, group to cls.company -> must be rejected
        with self.assertRaises(ValidationError):
            group.payment_token_id = token

    def test_validated_payment_mode_rejects_foreign_company(self):
        # company created before new(): creating a company clears the ORM
        # cache, which would wipe the in-memory new() record's values
        other = self.env["res.company"].create({"name": "Digital Seam Foreign Co"})
        self.mode.is_published = True
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(other)

    def test_validated_payment_mode_rejects_unpublished(self):
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        self.mode.is_published = False
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(self.company)

    def test_validated_payment_mode_rejects_archived(self):
        # archived modes are never offered by the render domain; a directly
        # posted id must not slip through either
        self.mode.is_published = True
        self.mode.active = False
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(self.company)

    def test_validated_payment_mode_accepts_published_same_company(self):
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        self.mode.is_published = True
        self.assertEqual(wizard._get_validated_payment_mode(self.company), self.mode)

    def test_validated_payment_mode_empty_selection(self):
        # flows without a payment step (e.g. Write&Pray) post no mode and
        # must yield an empty recordset, not an error
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "write_and_pray"}
        )
        self.assertFalse(wizard._get_validated_payment_mode(self.company))

    def test_wizard_update_converts_country(self):
        # the step form posts str ids; without an int conversion the ORM
        # silently drops the value and the sponsor loses their country
        child = self.env["compassion.child"].search([], limit=1)
        wizard = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": self.env.ref("base.public_user").id,
                "child_id": child.id,
            }
        )
        sweden = self.env.ref("base.se")
        wizard.update({"country": str(sweden.id)})
        self.assertEqual(wizard.country, sweden)

    def test_tokenization_required_for_sponsorship_context(self):
        provider = self.env["payment.provider"]
        self.assertFalse(provider._is_tokenization_required())
        self.assertTrue(provider._is_tokenization_required(my2_sponsorship=True))

    def test_done_tx_token_lands_on_group(self):
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        token = self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "provider_ref": "digital-seam-first-charge",
                "payment_details": "4242",
            }
        )
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-first-charge-tx",
                "operation": "online_direct",
                "tokenize": True,
                "token_id": token.id,
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        tx._set_done()
        tx._post_process()
        self.assertEqual(contract.group_id.payment_token_id, token)
        # the paid first invoice activates the contract through the
        # reconciliation chain
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.assertEqual(contract.state, "active")
        # paying another invoice of the group leaves the saved card alone
        token2 = token.copy({"provider_ref": "digital-seam-second-charge"})
        tx2 = tx.copy(
            {
                "reference": "digital-seam-second-charge-tx",
                "token_id": token2.id,
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        tx2._set_done()
        tx2._post_process()
        self.assertEqual(contract.group_id.payment_token_id, token)
        # the update-card page stamps the group on the tx and may replace it
        tx3 = tx.copy(
            {
                "reference": "digital-seam-card-update-tx",
                "token_id": token2.id,
                "invoice_ids": [Command.set(invoice.ids)],
                "my2_card_update_group_id": contract.group_id.id,
            }
        )
        tx3._set_done()
        tx3._post_process()
        self.assertEqual(contract.group_id.payment_token_id, token2)

    def test_ensure_first_invoice_sync(self):
        contract = self._make_digital_contract()
        self.assertEqual(contract.state, "draft")
        inv1 = contract._ensure_first_invoice()
        self.assertEqual(inv1.state, "posted")
        self.assertEqual(inv1.payment_state, "not_paid")
        self.assertEqual(contract.state, "waiting")
        # idempotent: a second call returns the same invoice
        self.assertEqual(contract._ensure_first_invoice(), inv1)

    def test_digital_revert_noop_when_paid(self):
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-paid-tx",
                "operation": "online_direct",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        tx._set_done()
        tx._post_process()
        self.assertEqual(contract.state, "active")
        contract._revert_abandoned_digital_signup()
        self.assertEqual(contract.state, "active")
        self.assertEqual(invoice.state, "posted")

    def test_digital_revert_waits_while_pending(self):
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-pending-tx",
                "operation": "online_direct",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        tx._set_pending()
        # a 3DS challenge may still be in flight: no revert, no crash
        contract._revert_abandoned_digital_signup(reschedule=False)
        self.assertEqual(contract.state, "waiting")
        self.assertEqual(invoice.state, "posted")

    def test_digital_revert_waits_for_fresh_draft_tx(self):
        # a draft tx may be mid provider round-trip: grace, don't revert
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-fresh-draft-tx",
                "operation": "online_direct",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        contract._revert_abandoned_digital_signup(reschedule=False)
        self.assertEqual(contract.state, "waiting")
        self.assertEqual(invoice.state, "posted")

    def test_digital_revert_runs_as_public_user(self):
        # the job is scheduled from the public checkout session and executed
        # with that user: the cleanup must self-elevate
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        public_env_contract = contract.with_user(self.env.ref("base.public_user"))
        public_env_contract._revert_abandoned_digital_signup()
        self.assertEqual(contract.state, "cancelled")
        self.assertEqual(invoice.state, "cancel")

    def test_digital_revert_skips_staff_handled_contract(self):
        # staff activated the contract inside the revert window: a stale
        # revert must never undo their work
        contract = self._make_digital_contract()
        contract._ensure_first_invoice()
        contract.contract_active()
        contract._revert_abandoned_digital_signup()
        self.assertEqual(contract.state, "active")

    def test_cron_charges_due_digital_invoice(self):
        contract, invoice, token = self._make_chargeable_invoice()
        amount_due = invoice.amount_residual
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        tx = self.env["payment.transaction"].search(
            [("invoice_ids", "in", invoice.ids)]
        )
        self.assertEqual(len(tx), 1)
        self.assertEqual(tx.operation, "offline")
        self.assertEqual(tx.token_id, token)
        self.assertEqual(tx.provider_id, contract.payment_mode_id.payment_provider_id)
        self.assertEqual(tx.partner_id, contract.partner_id)
        self.assertEqual(tx.amount, amount_due)
        # done charges are post-processed on the spot: reconciled invoice,
        # activated contract - no shopper session exists to poll for it
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.assertEqual(contract.state, "active")
        # idempotency: a second run never creates a second charge
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            1,
        )

    def test_cron_skips_not_due_and_tokenless(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        invoice.invoice_date_due = fields.Date.today() + timedelta(days=10)
        tokenless_contract = self._make_digital_contract()
        tokenless_invoice = tokenless_contract._ensure_first_invoice()
        tokenless_invoice.invoice_date_due = fields.Date.today() - timedelta(days=1)
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertFalse(
            self.env["payment.transaction"].search(
                [("invoice_ids", "in", (invoice + tokenless_invoice).ids)]
            )
        )

    def test_cron_skips_bank_mode_invoice(self):
        contract = self._make_digital_contract()
        contract.group_id.payment_mode_id.payment_provider_id = False
        invoice = contract._ensure_first_invoice()
        invoice.invoice_date_due = fields.Date.today() - timedelta(days=1)
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertFalse(
            self.env["payment.transaction"].search([("invoice_ids", "in", invoice.ids)])
        )

    def test_cron_skips_invoice_with_open_tx(self):
        contract, invoice, token = self._make_chargeable_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-open-tx",
                "operation": "offline",
                "token_id": token.id,
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        tx._set_pending()
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            1,
        )

    def test_cron_skips_token_provider_drift(self):
        # the group token no longer belongs to the mode's provider (e.g. the
        # mode was re-pointed to a new provider account): never charge it
        contract, invoice, token = self._make_chargeable_invoice()
        other_provider = self.env["payment.provider"].create(
            {
                "name": "Digital Seam Drift Provider",
                "code": "none",
                "company_id": contract.company_id.id,
                "state": "test",
            }
        )
        contract.group_id.payment_mode_id.payment_provider_id = other_provider
        with self.assertLogs(level="WARNING") as logs:
            self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertFalse(
            self.env["payment.transaction"].search([("invoice_ids", "in", invoice.ids)])
        )
        self.assertTrue(any(invoice.name in message for message in logs.output))

    def test_cron_failed_charge_fires_handoff(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        handoffs = []

        def record_handoff(contract_self, failed_invoice, reason):
            handoffs.append((contract_self, failed_invoice, reason))

        with patch.object(
            self.registry["recurring.contract"],
            "_on_digital_charge_failed",
            record_handoff,
        ):
            self._run_charge_cron(lambda tx_self: tx_self._set_error("Card expired"))
        self.assertEqual(len(handoffs), 1)
        failed_contracts, failed_invoice, reason = handoffs[0]
        self.assertEqual(failed_contracts, contract)
        self.assertEqual(failed_invoice, invoice)
        self.assertEqual(reason, "Card expired")
        self.assertEqual(contract.state, "waiting")

    def test_cron_one_failure_never_aborts_batch(self):
        contract_a, invoice_a, _ta = self._make_chargeable_invoice()
        contract_b, invoice_b, _tb = self._make_chargeable_invoice()

        def send(tx_self):
            if tx_self.invoice_ids == invoice_a:
                raise RuntimeError("unexpected crash")
            tx_self._set_done()

        self._run_charge_cron(send)
        self.assertIn(invoice_b.payment_state, ("paid", "in_payment"))
        self.assertEqual(contract_b.state, "active")
        self.assertEqual(invoice_a.payment_state, "not_paid")
        # the interrupted attempt survives as a draft: it cannot be proven
        # not to have reached the provider, so it must keep blocking
        drafts = self.env["payment.transaction"].search(
            [("invoice_ids", "in", invoice_a.ids)]
        )
        self.assertEqual(drafts.mapped("state"), ["draft"])
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(invoice_a.payment_state, "not_paid")
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice_a.ids)]
            ),
            1,
        )

    def test_cron_blocks_on_any_draft_tx(self):
        # a draft transaction - a crashed attempt or a live checkout
        # session - blocks the automatic charge regardless of its age
        _contract, invoice, token = self._make_chargeable_invoice()
        provider = token.provider_id
        method = self.env["payment.method"].search([], limit=1)
        draft = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": invoice.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-stale-draft",
                "operation": "online_direct",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        self.env.cr.execute(
            "UPDATE payment_transaction SET create_date = create_date"
            " - interval '2 hours' WHERE id = %s",
            [draft.id],
        )
        draft.invalidate_recordset()
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            1,
        )

    def test_due_digital_invoices_selection(self):
        contract, invoice, token = self._make_chargeable_invoice()
        group = contract.group_id
        self.assertEqual(group._due_digital_invoices(), invoice)
        # a consumed (errored) attempt keeps the invoice payable: paying it
        # with a fresh card is the update-card page's purpose
        self._run_charge_cron(lambda tx_self: tx_self._set_error("Card expired"))
        self.assertEqual(group._due_digital_invoices(), invoice)
        # an open transaction excludes it (a payment may be in flight)
        method = self.env["payment.method"].search([], limit=1)
        open_tx = self.env["payment.transaction"].create(
            {
                "provider_id": token.provider_id.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "digital-seam-due-open-tx",
                "operation": "offline",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        open_tx._set_pending()
        self.assertFalse(group._due_digital_invoices())
        open_tx._set_error("gone")
        # future-due invoices are never offered
        invoice.invoice_date_due = fields.Date.today() + timedelta(days=10)
        self.assertFalse(group._due_digital_invoices())

    def test_validation_tx_swaps_group_token(self):
        contract, _invoice, token = self._make_chargeable_invoice()
        group = contract.group_id
        method = self.env["payment.method"].search([], limit=1)
        new_token = token.copy({"provider_ref": "digital-seam-new-card"})
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": token.provider_id.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "amount": 0,
                "currency_id": group.company_id.currency_id.id,
                "reference": "digital-seam-validation-swap",
                "operation": "validation",
                "token_id": new_token.id,
                "my2_card_update_group_id": group.id,
            }
        )
        tx._set_done()
        tx._post_process()
        self.assertEqual(group.payment_token_id, new_token)

    def test_stale_checkout_tx_cleanup(self):
        # an abandoned pay-click leaves a draft that must stop blocking the
        # group's invoices, while pending and finished charges are kept
        contract, invoice, token = self._make_chargeable_invoice()
        method = self.env["payment.method"].search([], limit=1)

        def make_tx(reference):
            return self.env["payment.transaction"].create(
                {
                    "provider_id": token.provider_id.id,
                    "payment_method_id": method.id,
                    "partner_id": contract.partner_id.id,
                    "amount": invoice.amount_residual,
                    "currency_id": invoice.currency_id.id,
                    "reference": reference,
                    "operation": "online_direct",
                    "invoice_ids": [Command.set(invoice.ids)],
                }
            )

        abandoned = make_tx("digital-seam-abandoned-click")
        self.assertEqual(abandoned.state, "draft")
        self.assertFalse(contract.group_id._due_digital_invoices())
        # the job runs with the public user of the checkout session
        abandoned.with_user(
            self.env.ref("base.public_user")
        )._my2_cancel_stale_checkout_tx()
        self.assertEqual(abandoned.state, "cancel")
        self.assertEqual(contract.group_id._due_digital_invoices(), invoice)
        # a pending charge is left alone because the provider may still
        # settle it, so only the sweeper closes it
        in_flight = make_tx("digital-seam-abandoned-3ds")
        in_flight._set_pending()
        in_flight._my2_cancel_stale_checkout_tx()
        self.assertEqual(in_flight.state, "pending")
        finished = make_tx("digital-seam-finished-checkout")
        finished._set_done()
        finished._my2_cancel_stale_checkout_tx()
        self.assertEqual(finished.state, "done")

    def test_stale_pending_charge_is_swept(self):
        # a pending charge whose outcome never arrives is given up on, so
        # the invoice reopens and the contracts reach the dunning hook
        contract, invoice, _token = self._make_chargeable_invoice()

        def send_pending(tx_self):
            tx_self._set_pending()

        self._run_charge_cron(send_pending)
        tx = invoice.transaction_ids
        self.assertEqual(tx.state, "pending")
        self.assertFalse(contract.group_id._due_digital_invoices())
        Group = self.env["recurring.contract.group"]
        # still inside the provider's window, so nothing happens yet
        Group._cron_sweep_stale_pending_charges()
        self.assertEqual(tx.state, "pending")
        timeout = Group._my2_pending_charge_timeout_days(tx.provider_id)
        tx.last_state_change = fields.Datetime.now() - timedelta(days=timeout + 1)
        failures = []
        with patch.object(
            self.registry["recurring.contract"],
            "_on_digital_charge_failed",
            lambda self_, inv, reason: failures.append((inv, reason)),
        ):
            Group._cron_sweep_stale_pending_charges()
        self.assertEqual(tx.state, "error")
        self.assertTrue(failures)
        # the invoice is collectable again once the dead charge is closed
        self.assertEqual(contract.group_id._due_digital_invoices(), invoice)

    def test_charge_context_is_neutral_by_default(self):
        # provider-specific recovery opt-ins are extension-module business
        _contract, invoice, _token = self._make_chargeable_invoice()
        self.assertEqual(
            self.env["recurring.contract.group"]._digital_charge_context(invoice),
            {},
        )

    def test_staff_button_recharges_after_failure(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        self._run_charge_cron(lambda tx_self: tx_self._set_error("Card expired"))
        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertTrue(invoice.my2_can_charge_digital)
        # the failed attempt consumed the invoice's automatic charge: the
        # cron never re-charges, only the forced staff action does
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(invoice.payment_state, "not_paid")
        with patch.object(
            self.registry["payment.transaction"],
            "_send_payment_request",
            lambda tx_self: tx_self._set_done(),
        ):
            invoice.action_charge_digital_invoice()
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.assertEqual(contract.state, "active")
        self.assertFalse(invoice.my2_can_charge_digital)

    def test_staff_button_never_doubles_open_or_paid_charge(self):
        _contract, invoice, _token = self._make_chargeable_invoice()

        def send_pending(tx_self):
            tx_self._set_pending()

        self._run_charge_cron(send_pending)
        # a pending charge is offered to staff, who check the provider
        # dashboard before recovering the invoice
        self.assertTrue(invoice.my2_can_charge_digital)
        with patch.object(
            self.registry["payment.transaction"],
            "_send_payment_request",
            lambda tx_self: tx_self._set_done(),
        ):
            invoice.action_charge_digital_invoice()
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            2,
        )
        # the charge that succeeded is money, so the button closes for good
        self.assertFalse(invoice.my2_can_charge_digital)
        with self.assertRaises(UserError):
            invoice.action_charge_digital_invoice()
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            2,
        )

    def test_staff_button_refuses_while_a_draft_is_in_flight(self):
        _contract, invoice, _token = self._make_chargeable_invoice()

        def stay_draft(tx_self):
            return None

        self._run_charge_cron(stay_draft)
        # a draft may still be finishing at the provider, so nothing may
        # charge the invoice again until it settles
        self.assertFalse(invoice.my2_can_charge_digital)
        with self.assertRaises(UserError):
            invoice.action_charge_digital_invoice()
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            1,
        )

    def test_digital_revert_cancels_abandoned(self):
        child = self.env["compassion.child"].search(
            [("state", "=", "N"), ("hold_id", "!=", False)], limit=1
        )
        if not child:
            # stage one: the shared dev database may have no held child left
            child = self.env["compassion.child"].search(
                [("sponsor_id", "=", False), ("state", "in", ("R", "W"))], limit=1
            )
            self.assertTrue(child, "the database needs an unsponsored child")
            hold = self.env["compassion.hold"].create(
                {
                    "child_id": child.id,
                    "type": "E-Commerce Hold",
                    "expiration_date": fields.Datetime.now() + timedelta(days=1),
                }
            )
            child.write({"state": "N", "hold_id": hold.id})
        child.write(
            {
                "website_reservation_date": "2026-01-01 00:00:00",
                "website_reservation_id": "digital-seam-reservation",
            }
        )
        contract = self._make_digital_contract(child=child)
        partner = contract.partner_id
        invoice = contract._ensure_first_invoice()
        # no transaction at all: the sponsor closed the payment page.
        # get_lifecycle_event is a live GMC fetch tail-ending
        # child_unsponsored - out of scope here.
        with patch.object(
            self.registry["compassion.child"],
            "get_lifecycle_event",
            lambda child_self: [],
        ):
            contract._revert_abandoned_digital_signup()
        self.assertEqual(contract.state, "cancelled")
        self.assertEqual(invoice.state, "cancel")
        self.assertEqual(child.state, "N")
        self.assertFalse(child.sponsor_id)
        self.assertFalse(child.website_reservation_id)
        self.assertFalse(child.website_reservation_date)
        self.assertTrue(partner.exists())
