from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)
from odoo.addons.website.tools import MockRequest

from ..controllers.my2_sponsorships import (
    CARDHOLDER_NAME_SESSION_KEY,
    SponsorshipPayment,
)
from .common import PayuDigitalCase


@tagged("post_install", "-at_install")
class TestCardholderName(PayuDigitalCase):
    """The fast checkout of a company offering PayU asks the name on the card
    under the e-mail, and the card form of the payment page takes it."""

    def setUp(self):
        super().setUp()
        self.website = self.env.ref("my_compassion.my2_website")
        self.child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(self.child, "the database needs a child")
        self.website_company = self.env["res.company"].create({"name": "Cardholder Co"})
        self.provider = self.env["payment.provider"].create(
            {
                "name": "Cardholder PayU",
                "code": "payu_gpo",
                "company_id": self.website_company.id,
                "state": "test",
                "payu_gpo_pos_id": "300746",
                "payu_gpo_client_id": "300746",
                "payu_gpo_client_secret": "test-client-secret",
                "payu_gpo_second_key": "test-second-key",
                "payment_method_ids": [
                    Command.link(self.env.ref("payment.payment_method_card").id)
                ],
            }
        )
        self.payu_mode = self._make_mode("Cardholder PayU", self.provider)

    def _make_mode(self, name, provider=None):
        return self.env["account.payment.mode"].create(
            {
                "name": name,
                "company_id": self.website_company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": provider.id if provider else False,
                "is_published": True,
            }
        )

    def _wizard(self, sponsorship_type="standard"):
        return self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": sponsorship_type,
                "user_id": self.env.ref("base.public_user").id,
                "child_id": self.child.id,
                "company_id": self.website_company.id,
            }
        )

    def _render(self, wizard):
        with MockRequest(self.env, website=self.website):
            return str(
                MyCompassionNewSponsorshipController._render_form_content(wizard)
            )

    def test_asked_under_the_email_with_payu(self):
        html = self._render(self._wizard())
        self.assertIn('name="cardholder_name"', html)
        self.assertLess(
            html.index('name="email"'), html.index('name="cardholder_name"')
        )

    def test_not_asked_without_payu(self):
        self.payu_mode.payment_provider_id = False
        wizard = self._wizard()
        self.assertFalse(wizard._my2_asks_cardholder_name())
        self.assertNotIn('name="cardholder_name"', self._render(wizard))

    def test_not_asked_by_write_and_pray(self):
        self.assertFalse(self._wizard("write_and_pray")._my2_asks_cardholder_name())

    def test_typed_name_is_normalized(self):
        wizard = self._wizard()
        wizard.update({"cardholder_name": "  Anna   Nowak "})
        self.assertEqual(wizard.cardholder_name, "Anna Nowak")

    def test_finish_refused_without_the_name(self):
        wizard = self._wizard()
        wizard.update(
            {
                "email": "anna@example.com",
                "privacy_consent": "on",
                "payment_method": str(self.payu_mode.id),
            }
        )
        with self.assertRaisesRegex(ValidationError, "name on the card"):
            wizard.finish_sponsorship()

    def test_payment_page_takes_the_name(self):
        contract, invoice, _token = self._make_payu_chargeable_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        partner = contract.partner_id
        for placeholder, expected in ((True, "Anna Nowak"), (False, None)):
            partner.my2_name_placeholder = placeholder
            with MockRequest(self.env, website=self.website) as request:
                request.session[CARDHOLDER_NAME_SESSION_KEY] = "Anna Nowak"
                values = SponsorshipPayment._get_sponsorship_payment_values(
                    contract, provider, "token", invoice
                )
            self.assertEqual(values.get("payu_gpo_cardholder_name"), expected)

    def test_card_form_hides_the_prefilled_name(self):
        pm = self.env.ref("payment.payment_method_card")
        html = str(
            self.env["ir.qweb"]._render(
                "payment_payu_gpo.inline_form",
                {
                    "provider_sudo": self.provider,
                    "pm_sudo": pm,
                    "payu_gpo_cardholder_name": "Anna Nowak",
                },
            )
        )
        self.assertIn('value="Anna Nowak"', html)
        self.assertIn('class="mt-2 d-none"', html)
