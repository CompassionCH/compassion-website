from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestFastCheckoutPlumbing(DigitalSeamCase):
    """The shared plumbing of the pay-first checkout: a partner may reach the
    payment provider before their name is known, and everything that greets
    them by name waits for it."""

    # === Crash-on-empty-name (pre-existing bugs) ===

    def test_matching_tolerates_falsy_name_parts(self):
        # both parts falsy: the rules have nothing to search on and must fall
        # through, not raise TypeError on "False + ' ' + False"
        partner = self.env["res.partner.match"].match_values_to_partner(
            {
                "email": "fast-checkout-nameless@example.org",
                "firstname": False,
                "lastname": False,
                "zip": False,
            },
            match_create=False,
        )
        self.assertFalse(partner)

    def test_matching_tolerates_one_name_part(self):
        known = self.env["res.partner"].create(
            {
                "lastname": "Onepart",
                "email": "fast-checkout-onepart@example.org",
            }
        )
        matched = self.env["res.partner.match"].match_values_to_partner(
            {
                "email": "fast-checkout-onepart@example.org",
                "firstname": False,
                "lastname": "Onepart",
                "zip": False,
            },
            match_create=False,
        )
        self.assertEqual(matched, known)

    def test_transaction_partner_name_never_blank(self):
        # Adyen splits partner_name for both the drop-in payment and the
        # monthly off-session charge, and the splitter raises on an empty
        # value. Legacy rows with no name at all exist, so the snapshot is
        # forced to something splittable.
        partner = self.env["res.partner"].create({"lastname": "Blankable"})
        partner.flush_recordset()
        self.env.cr.execute(
            "UPDATE res_partner SET name = NULL WHERE id = %s", [partner.id]
        )
        partner.invalidate_recordset(["name"])
        contract = self._make_digital_contract()
        provider = contract.payment_mode_id.payment_provider_id
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": partner.id,
                "amount": 100,
                "currency_id": contract.company_id.currency_id.id,
                "reference": "fast-checkout-nameless-tx",
                "operation": "online_direct",
            }
        )
        self.assertEqual(tx.partner_name, self.env["res.partner"].MY2_PLACEHOLDER_NAME)

    # === Steps and the deferred-details signal ===

    def test_public_flows_run_the_fast_checkout_step(self):
        wizard_model = self.env["new.sponsorship.wizard"]
        fast_step = "my_compassion.new_sponsorship_wizard_step_fast_checkout"
        for sponsorship_type in ("standard", "write_and_pray"):
            with self.subTest(sponsorship_type=sponsorship_type):
                public = wizard_model._get_step_xmlids(sponsorship_type, True)
                self.assertEqual(public[0], fast_step)
                self.assertNotIn(
                    "my_compassion.new_sponsorship_wizard_step_user_details",
                    public,
                )
                self.assertNotIn(
                    "my_compassion.new_sponsorship_wizard_step_communication_details",
                    public,
                )
                # a logged-in sponsor is already identified: untouched
                logged_in = wizard_model._get_step_xmlids(sponsorship_type, False)
                self.assertNotIn(fast_step, logged_in)
                self.assertEqual(
                    logged_in,
                    wizard_model.STEPS_CONFIGS[sponsorship_type]["logged_in"],
                )

    def test_details_deferred_only_for_the_fast_checkout(self):
        child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(child, "the database needs a child")
        public = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": self.env.ref("base.public_user").id,
                "child_id": child.id,
            }
        )
        self.assertTrue(public.details_deferred)
        logged_in = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": self.env.user.id,
                "child_id": child.id,
            }
        )
        self.assertFalse(logged_in.details_deferred)

    def test_placeholder_only_when_no_name_was_given(self):
        child = self.env["compassion.child"].search([], limit=1)
        wizard = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": self.env.ref("base.public_user").id,
                "child_id": child.id,
                "email": "fast-checkout-placeholder@example.org",
                "privacy_consent": True,
            }
        )
        vals = wizard._get_new_partner_vals()
        self.assertTrue(vals["my2_name_placeholder"])
        self.assertEqual(vals["lastname"], self.env["res.partner"].MY2_PLACEHOLDER_NAME)
        self.assertFalse(vals["firstname"])
        # a name typed in (a country extension keeping the identity step, a
        # logged-in prefill) is never replaced by the placeholder
        wizard.write({"firstname": "Given", "lastname": "Name"})
        vals = wizard._get_new_partner_vals()
        self.assertNotIn("my2_name_placeholder", vals)
        self.assertEqual(vals["lastname"], "Name")

    # === Placeholder replacement ===

    def test_placeholder_name_replaced_once(self):
        partner = self.env["res.partner"].create(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "my2_name_placeholder": True,
                "email": "fast-checkout-replace@example.org",
            }
        )
        updated = partner._my2_replace_placeholder_name("John Michael", "Smith")
        self.assertEqual(updated, partner)
        self.assertEqual(partner.firstname, "John Michael")
        self.assertEqual(partner.lastname, "Smith")
        self.assertFalse(partner.my2_name_placeholder)
        # a late notification must never overwrite the real name
        self.assertFalse(partner._my2_replace_placeholder_name("Someone", "Else"))
        self.assertEqual(partner.lastname, "Smith")

    def test_cardholder_name_from_notification(self):
        contract = self._make_digital_contract()
        partner = contract.partner_id
        partner.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        invoice = contract._ensure_first_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": partner.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "fast-checkout-cardholder-tx",
                "operation": "online_direct",
                "my2_cardholder_name": "Jean Michel Dupont",
            }
        )
        tx._set_done()
        tx._post_process()
        self.assertFalse(partner.my2_name_placeholder)
        self.assertEqual(partner.firstname, "Jean Michel")
        self.assertEqual(partner.lastname, "Dupont")

    def test_cardholder_name_extraction_per_provider(self):
        tx_model = self.env["payment.transaction"]
        self.assertEqual(
            tx_model._my2_cardholder_name_stripe(
                {"charge": {"billing_details": {"name": "Ada Lovelace"}}}
            ),
            "Ada Lovelace",
        )
        self.assertEqual(
            tx_model._my2_cardholder_name_stripe(
                {
                    "payment_intent": {
                        "charges": {
                            "data": [{"billing_details": {"name": "Grace Hopper"}}]
                        }
                    }
                }
            ),
            "Grace Hopper",
        )
        self.assertEqual(
            tx_model._my2_cardholder_name_adyen(
                {"additionalData": {"cardHolderName": "Alan Turing"}}
            ),
            "Alan Turing",
        )
        self.assertEqual(
            tx_model._my2_cardholder_name_adyen(
                {"shopperName": {"firstName": "Alan", "lastName": "Turing"}}
            ),
            "Alan Turing",
        )
        # the settings behind those fields are off by default on Adyen, and
        # PostFinance has no known field at all: both degrade to "ask the
        # sponsor", never to an error
        self.assertEqual(tx_model._my2_cardholder_name_adyen({}), "")
        self.assertEqual(
            tx_model._my2_cardholder_name_postfinance({"resultCode": "Authorised"}),
            "",
        )
        self.assertEqual(tx_model._my2_cardholder_name_stripe({"charge": None}), "")

    # === Details-form token ===

    def test_details_token_lifecycle(self):
        contract = self._make_digital_contract()
        contract.my2_signup = True
        contract.partner_id.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        token = contract._my2_issue_details_token()
        self.assertTrue(token)
        self.assertTrue(contract._my2_check_details_token(token))
        self.assertFalse(contract._my2_check_details_token("wrong-token"))
        self.assertFalse(contract._my2_check_details_token(False))
        # expired
        contract.my2_details_token_expiration = fields.Datetime.now() - timedelta(
            minutes=1
        )
        self.assertFalse(contract._my2_check_details_token(token))
        # re-issuing invalidates the previous token
        new_token = contract._my2_issue_details_token()
        self.assertNotEqual(new_token, token)
        self.assertFalse(contract._my2_check_details_token(token))
        # consumed on the first successful save
        contract._my2_consume_details_token()
        self.assertFalse(contract._my2_check_details_token(new_token))

    def test_details_token_refused_once_the_name_is_real(self):
        contract = self._make_digital_contract()
        contract.my2_signup = True
        contract.partner_id.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        token = contract._my2_issue_details_token()
        contract.partner_id._my2_replace_placeholder_name("Real", "Sponsor")
        self.assertFalse(contract._my2_check_details_token(token))
        # and nothing is minted for a signup that wants no details
        self.assertFalse(contract._my2_issue_details_token())

    # === Portal invitation sequencing ===

    def test_portal_invitation_waits_for_a_real_name(self):
        contract = self._make_digital_contract()
        contract.my2_signup = True
        contract.partner_id.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        invoice = contract._ensure_first_invoice()
        invoice.invoice_line_ids.contract_id.contract_active()
        # the contract still activates on payment: only the invitation waits
        self.assertEqual(contract.state, "active")
        self.assertFalse(contract._my2_pending_portal_invitations())
        contract.partner_id._my2_replace_placeholder_name("Real", "Sponsor")
        self.assertEqual(contract._my2_pending_portal_invitations(), contract)
