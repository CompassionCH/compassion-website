from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment import utils as payment_utils

from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestCardholderNameCapture(DigitalSeamCase):
    """A provider-reported cardholder name counts only when it is a name,
    and the details form outlives it only where it is a required step.

    Core hands the provider the partner's name as the payer's, and for a
    fast-checkout sponsor that value is the "(pending)" placeholder, so the
    provider can echo it back on its confirmed-payment notification.
    """

    def setUp(self):
        super().setUp()
        self.signup = self._make_digital_contract()
        partner_model = self.env["res.partner"]
        self.signup.partner_id.write(
            {
                "lastname": partner_model.MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": "cardholder-capture@example.org",
            }
        )
        self.signup.write({"my2_signup": True, "my2_details_awaited": True})
        self.partner = self.signup.partner_id

    def _transaction(self, cardholder_name):
        provider = self.signup.payment_mode_id.payment_provider_id
        transaction = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": self.partner.id,
                "amount": 100,
                "currency_id": self.signup.company_id.currency_id.id,
                "reference": f"cardholder-capture-{self.partner.id}",
                "operation": "online_direct",
            }
        )
        transaction.my2_cardholder_name = cardholder_name
        return transaction

    def _mandatory(self, mandatory=True):
        return patch.object(
            type(self.signup), "_my2_details_mandatory", return_value=mandatory
        )

    # === What counts as a name ===

    def test_placeholder_echo_never_becomes_the_name(self):
        """The provider reporting the placeholder back must not be taken for
        the sponsor's name: it would clear my2_name_placeholder and with it
        the details form, and "(pending)" would be their name."""
        placeholder = self.env["res.partner"].MY2_PLACEHOLDER_NAME

        self._transaction(placeholder)._my2_apply_cardholder_name()

        self.assertTrue(self.partner.my2_name_placeholder)
        self.assertTrue(self.signup._my2_details_pending())

    def test_placeholder_is_recognised_in_any_case(self):
        self.assertFalse(
            self.env["payment.transaction"]._my2_is_usable_cardholder_name(
                f"  {self.env['res.partner'].MY2_PLACEHOLDER_NAME.upper()} "
            )
        )

    def test_whitespace_only_name_is_not_a_name(self):
        """split_partner_name raises IndexError on a string that splits to
        nothing, so whitespace must never reach it."""
        self._transaction("   ")._my2_apply_cardholder_name()

        self.assertTrue(self.partner.my2_name_placeholder)

    def test_real_name_is_applied(self):
        self._transaction("Anna Maria Svensson")._my2_apply_cardholder_name()

        self.assertFalse(self.partner.my2_name_placeholder)
        self.assertEqual(self.partner.firstname, "Anna Maria")
        self.assertEqual(self.partner.lastname, "Svensson")

    def test_prefill_ignores_the_placeholder_echo(self):
        invoice = self.signup._ensure_first_invoice()
        transaction = self._transaction(self.env["res.partner"].MY2_PLACEHOLDER_NAME)
        transaction.invoice_ids = invoice

        prefill = self.signup._my2_details_prefill()

        self.assertEqual((prefill["firstname"], prefill["lastname"]), ("", ""))

    # === How long the details form stays due ===

    def test_provider_name_ends_an_optional_form(self):
        """Where the form only exists to ask the name, a name from the
        provider is the end of it."""
        with self._mandatory(False):
            self._transaction("Anna Svensson")._my2_apply_cardholder_name()

            self.assertFalse(self.signup._my2_details_pending())

    def test_mandatory_form_outlives_the_provider_name(self):
        with self._mandatory():
            self._transaction("Anna Svensson")._my2_apply_cardholder_name()

            self.assertTrue(self.signup._my2_details_pending())
            self.assertTrue(self.signup._my2_issue_details_token())

    def test_mandatory_form_ends_once_submitted(self):
        with self._mandatory():
            self._transaction("Anna Svensson")._my2_apply_cardholder_name()
            self.signup._my2_issue_details_token()

            self.signup._my2_apply_details(
                {
                    "firstname": "Anna",
                    "lastname": "Svensson",
                    "phone": "+46 70 123 45 67",
                }
            )

            self.assertFalse(self.signup._my2_details_pending())
            self.assertFalse(self.signup.my2_details_awaited)

    def test_mandatory_form_never_opens_for_a_returning_sponsor(self):
        """A signup by a sponsor who already had a name never awaited any
        details, so the form must not open on their partner."""
        self.partner.write(
            {
                "firstname": "Returning",
                "lastname": "Sponsor",
                "my2_name_placeholder": False,
            }
        )
        self.signup.my2_details_awaited = False
        with self._mandatory():
            self.assertFalse(self.signup._my2_details_pending())

    # === Splitting the provider's single name string ===

    def test_split_partner_name_handles_nordic_names(self):
        """Core's splitter keeps every given name with the firstname and
        treats the final token as the surname, which is what Nordic naming
        needs."""
        cases = [
            ("Anna Svensson", ("Anna", "Svensson")),
            ("Anna Maria Svensson", ("Anna Maria", "Svensson")),
            ("Ole Kristian Nordmann", ("Ole Kristian", "Nordmann")),
            ("Mette-Marie Hansen", ("Mette-Marie", "Hansen")),
            ("Pekka", ("Pekka", "")),
        ]
        for full_name, expected in cases:
            with self.subTest(full_name=full_name):
                self.assertEqual(payment_utils.split_partner_name(full_name), expected)
