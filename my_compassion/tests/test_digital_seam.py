from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDigitalSeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Digital Seam Test Co"})
        cls.partner = cls.env["res.partner"].create({"name": "Digital Seam Sponsor"})
        cls.pay_method = cls.env.ref("my_compassion.payment_method_psp_token")
        cls.mode = cls.env["account.payment.mode"].create(
            {
                "name": "Digital Seam Test Mode",
                "company_id": cls.company.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.pay_method.id,
                "payment_order_ok": False,
            }
        )

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
        self.assertEqual(
            wizard._get_validated_payment_mode(self.company), self.mode
        )

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

    def _make_digital_contract(self, child=None):
        """A contract on a provider-backed mode, in a company with a working
        sale accounting setup, with a plain product line. Child-less (no
        GMC) unless a child is passed."""
        journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
        self.assertTrue(journal, "the database needs one company with sale accounting")
        company = journal.company_id
        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        # the payment chain needs an account.payment.method matching the
        # provider code to build the journal's payment method line
        if not self.env["account.payment.method"].search(
            [("code", "=", "none"), ("payment_type", "=", "inbound")]
        ):
            self.env["account.payment.method"].sudo().create(
                {"name": "Demo", "code": "none", "payment_type": "inbound"}
            )
        provider = self.env["payment.provider"].create(
            {
                "name": "Digital Seam Pay Provider",
                "code": "none",
                "company_id": company.id,
                "journal_id": bank_journal.id,
                "state": "test",
            }
        )
        provider._ensure_payment_method_line()
        mode = self.env["account.payment.mode"].create(
            {
                "name": "Digital Seam Pay Mode",
                "company_id": company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": provider.id,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Digital Seam Payer",
                "country_id": self.env.ref("base.se").id,
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            partner, company, mode
        )
        product = self.env["product.product"].search(
            [
                ("default_code", "=", "sponsorship"),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
        )
        self.assertTrue(product, "the database needs the sponsorship product")
        vals = {
            "partner_id": partner.id,
            "group_id": group.id,
            "type": "O",
            "contract_line_ids": [
                Command.create(
                    {"product_id": product.id, "amount": 100, "quantity": 1}
                )
            ],
        }
        if child:
            vals.update({"type": "S", "child_id": child.id})
        return (
            self.env["recurring.contract"].with_context(no_upsert=True).create(vals)
        )

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
        # a later transaction with a fresh token replaces the group token
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

    def test_digital_revert_cancels_abandoned(self):
        child = self.env["compassion.child"].search(
            [("state", "=", "N"), ("hold_id", "!=", False)], limit=1
        )
        self.assertTrue(child, "the database needs an available held child")
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
