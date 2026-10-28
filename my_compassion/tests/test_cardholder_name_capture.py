import json

from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils

from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestCardholderNameCapture(DigitalSeamCase):
    """A provider-reported cardholder name counts only when it is a name.

    Core hands the provider partner.name as the billing-details default
    (payment_stripe's _stripe_get_inline_form_values and
    _stripe_create_customer both do), and for a fast-checkout sponsor that
    value is the "(pending)" placeholder. The provider echoes it back on its
    confirmed-payment notification, so the capture path is offered the
    placeholder as the sponsor's own name.
    """

    def _placeholder_partner(self):
        partner_model = self.env["res.partner"]
        return partner_model.create(
            {
                "lastname": partner_model.MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": "cardholder-capture@example.org",
                # recurring_contract.country_id is NOT NULL and comes from the
                # partner, so a country-less sponsor cannot hold a contract.
                "country_id": self.env.ref("base.se").id,
            }
        )

    def _transaction_for(self, partner, cardholder_name):
        contract = self._make_digital_contract()
        provider = contract.payment_mode_id.payment_provider_id
        transaction = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": partner.id,
                "amount": 100,
                "currency_id": contract.company_id.currency_id.id,
                "reference": f"cardholder-capture-{partner.id}",
                "operation": "online_direct",
            }
        )
        transaction.my2_cardholder_name = cardholder_name
        return transaction

    # === The leak ===

    def test_placeholder_echo_never_becomes_the_name(self):
        """The provider reporting our own placeholder back must not be taken
        for the sponsor's name. Applying it clears my2_name_placeholder, and
        that flag is what _my2_details_pending keys on - so the details form
        would stop rendering and the sponsor would never be asked at all."""
        partner = self._placeholder_partner()
        placeholder = self.env["res.partner"].MY2_PLACEHOLDER_NAME
        transaction = self._transaction_for(partner, placeholder)

        transaction._my2_apply_cardholder_name()

        self.assertTrue(
            partner.my2_name_placeholder,
            "the placeholder echo was taken for a real name",
        )
        self.assertNotEqual(partner.firstname, placeholder)
        self.assertEqual(partner.name, placeholder)

    def test_placeholder_echo_keeps_the_details_form_alive(self):
        """The consequence the previous test exists to prevent."""
        partner = self._placeholder_partner()
        transaction = self._transaction_for(
            partner, self.env["res.partner"].MY2_PLACEHOLDER_NAME
        )
        contract = self._make_digital_contract()
        contract.write(
            {
                "partner_id": partner.id,
                "correspondent_id": partner.id,
                "my2_signup": True,
            }
        )

        transaction._my2_apply_cardholder_name()

        self.assertTrue(
            contract._my2_details_pending(),
            "the sponsor can no longer be asked for their name",
        )

    def test_whitespace_only_name_is_not_a_name(self):
        partner = self._placeholder_partner()
        transaction = self._transaction_for(partner, "   ")

        transaction._my2_apply_cardholder_name()

        self.assertTrue(partner.my2_name_placeholder)

    # === Still works for a real name ===

    def test_real_name_is_applied(self):
        partner = self._placeholder_partner()
        transaction = self._transaction_for(partner, "Anna Maria Svensson")

        transaction._my2_apply_cardholder_name()

        self.assertFalse(partner.my2_name_placeholder)
        self.assertEqual(partner.firstname, "Anna Maria")
        self.assertEqual(partner.lastname, "Svensson")

    # === The root cause: what Stripe is offered in the first place ===

    def _stripe_billing_details_for(self, partner):
        # Copy the stock record rather than create one: a bare create lacks
        # the inline form view reference, and the provider refuses to exist
        # in any state without its key pair.
        provider = (
            self.env.ref("payment.payment_provider_stripe")
            .sudo()
            .copy(
                {
                    "state": "test",
                    "stripe_publishable_key": "pk_test_dummy",
                    "stripe_secret_key": "sk_test_dummy",
                }
            )
        )
        method = self.env.ref("payment.payment_method_card").sudo()
        method.active = True
        raw = provider._stripe_get_inline_form_values(
            100.0,
            self.env.company.currency_id,
            partner.id,
            False,
            payment_method_sudo=method,
        )
        return json.loads(raw)["billing_details"]

    def test_placeholder_is_not_sent_to_stripe(self):
        """The fix at source: a placeholder must never reach the Payment
        Element as the payer's name, or Stripe hands it straight back."""
        partner = self._placeholder_partner()

        billing_details = self._stripe_billing_details_for(partner)

        self.assertEqual(billing_details["name"], "")
        # everything else still goes through - only the name is withheld
        self.assertEqual(billing_details["email"], partner.email)

    def test_real_name_is_still_sent_to_stripe(self):
        partner = self.env["res.partner"].create(
            {
                "firstname": "Anna",
                "lastname": "Svensson",
                "email": "anna@example.org",
            }
        )

        billing_details = self._stripe_billing_details_for(partner)

        self.assertEqual(billing_details["name"], "Anna Svensson")

    # === Requirement 3: core's split is the right one for Nordic names ===

    def test_split_partner_name_handles_nordic_names(self):
        """Decision 8 of T3465: no custom parser. Core's splitter keeps every
        given name with the firstname and treats the final token as the
        surname, which is what Nordic naming needs."""
        cases = [
            ("Anna Svensson", ("Anna", "Svensson")),
            ("Anna Maria Svensson", ("Anna Maria", "Svensson")),
            ("Ole Kristian Nordmann", ("Ole Kristian", "Nordmann")),
            ("Mette-Marie Hansen", ("Mette-Marie", "Hansen")),
            ("Pekka", ("Pekka", "")),
        ]
        for full_name, expected in cases:
            with self.subTest(full_name=full_name):
                self.assertEqual(
                    payment_utils.split_partner_name(full_name), expected
                )
