import re
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)
from odoo.addons.my_compassion.models.my2_new_sponsorship_wizard import (
    NewSponsorshipWizard,
)
from odoo.addons.website.tools import MockRequest

from ..controllers.my2_sponsorships import (
    CARDHOLDER_NAMES_SESSION_KEY,
    NewSponsorshipController,
    SponsorshipPayment,
)
from ..utils import session_cardholder_names
from .common import PayuDigitalCase


@tagged("post_install", "-at_install")
class TestCardholderName(PayuDigitalCase):
    """The fast checkout of a company offering PayU asks the first and last
    name on the card under the e-mail, required by the PayU buttons only, and
    the card form of the payment page comes prefilled with them."""

    def setUp(self):
        super().setUp()
        self.website = self.env.ref("my_compassion.my2_website")
        child_model = self.env["compassion.child"]
        self.child = child_model.search(
            [("state", "in", child_model._available_states())], limit=1
        )
        self.assertTrue(self.child, "the database needs an available child")
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
        self.standing_order_mode = self._make_mode("Cardholder Standing Order")

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

    def _wizard(self, sponsorship_type="standard", **values):
        return self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": sponsorship_type,
                "user_id": self.env.ref("base.public_user").id,
                "child_id": self.child.id,
                "company_id": self.website_company.id,
                "email": "anna@example.com",
                "privacy_consent": True,
                **values,
            }
        )

    def _render(self, wizard):
        with MockRequest(self.env, website=self.website):
            return str(
                MyCompassionNewSponsorshipController._render_form_content(wizard)
            )

    def _patch_finish(self, sponsorship):
        """my_compassion's own finish, which creates the partner and the
        contract, replaced by an existing contract."""
        return patch.object(
            NewSponsorshipWizard, "finish_sponsorship", return_value=sponsorship
        )

    def _submit(self, request, wizard, sponsorship):
        with self._patch_finish(sponsorship):
            # The override's own route() is only merged with my_compassion's
            # when the routing map is built: call what it wraps.
            submit = NewSponsorshipController.sponsorship_wizard_submit
            submit.original_endpoint(
                NewSponsorshipController(), wizard_id=str(wizard.id)
            )
        return request.session.get(CARDHOLDER_NAMES_SESSION_KEY)

    # === The fast checkout ===

    def test_asked_under_the_email_with_payu(self):
        html = self._render(self._wizard())
        self.assertLess(
            html.index('name="email"'), html.index('name="cardholder_firstname"')
        )
        self.assertLess(
            html.index('name="cardholder_firstname"'),
            html.index('name="cardholder_lastname"'),
        )

    def test_required_by_the_payu_button_only(self):
        html = self._render(self._wizard())
        buttons = re.findall(r"<div[^>]*data-payment-mode=[^>]*>", html)
        self.assertEqual(len(buttons), 2)
        for button in buttons:
            self.assertEqual(
                'data-payu-gpo="1"' in button,
                f'data-payment-mode="{self.payu_mode.id}"' in button,
            )

    def test_not_asked_without_payu(self):
        self.payu_mode.payment_provider_id = False
        wizard = self._wizard()
        self.assertFalse(wizard._my2_asks_cardholder_name())
        html = self._render(wizard)
        self.assertNotIn('name="cardholder_firstname"', html)
        self.assertNotIn('name="cardholder_lastname"', html)

    def test_not_asked_with_payu_disabled(self):
        self.provider.state = "disabled"
        self.assertFalse(self._wizard()._my2_asks_cardholder_name())

    def test_not_asked_by_write_and_pray(self):
        self.assertFalse(self._wizard("write_and_pray")._my2_asks_cardholder_name())

    def test_typed_names_are_normalized(self):
        wizard = self._wizard()
        wizard.update(
            {"cardholder_firstname": "  Anna ", "cardholder_lastname": " Maria   Nowak"}
        )
        self.assertEqual(wizard.cardholder_firstname, "Anna")
        self.assertEqual(wizard.cardholder_lastname, "Maria Nowak")

    # === The finish ===

    def test_payu_refused_without_both_names(self):
        for names in ({}, {"cardholder_firstname": "Anna"}):
            wizard = self._wizard(payment_method=self.payu_mode.id, **names)
            with self.assertRaisesRegex(ValidationError, "last name on the card"):
                wizard.finish_sponsorship()

    def test_standing_order_finishes_without_the_name(self):
        contract = self._make_digital_contract()
        wizard = self._wizard(payment_method=self.standing_order_mode.id)
        with self._patch_finish(contract):
            self.assertEqual(wizard.finish_sponsorship(), contract)
        self.assertEqual(wizard.payu_gpo_sponsorship_id, contract)

    # === From the submit to the payment page ===

    def test_each_signup_gets_its_own_names(self):
        anna_contract, anna_invoice, _token = self._make_payu_chargeable_invoice()
        jan_contract = self._make_digital_contract()
        provider = anna_contract.payment_mode_id.payment_provider_id
        with MockRequest(self.env, website=self.website) as request:
            for contract, firstname in (
                (anna_contract, "Anna"),
                (jan_contract, "Jan"),
            ):
                wizard = self._wizard(payment_method=self.payu_mode.id)
                wizard.update(
                    {"cardholder_firstname": firstname, "cardholder_lastname": "Nowak"}
                )
                self._submit(request, wizard, contract)
            values = SponsorshipPayment._get_sponsorship_payment_values(
                anna_contract, provider, "token", anna_invoice
            )
            self.assertEqual(values["payu_gpo_cardholder_firstname"], "Anna")
            self.assertEqual(values["payu_gpo_cardholder_lastname"], "Nowak")
            # The thank-you page, once paid, drops the names of its signup only.
            NewSponsorshipController._thank_you_values(anna_contract)
            self.assertEqual(
                request.session[CARDHOLDER_NAMES_SESSION_KEY],
                {str(jan_contract.id): ["Jan", "Nowak"]},
            )

    def test_card_form_prefilled_with_the_sponsor_names(self):
        """Without names typed on the fast checkout (the full form), the card
        form comes prefilled with the sponsor's own, never a placeholder."""
        contract, invoice, _token = self._make_payu_chargeable_invoice()
        provider = contract.payment_mode_id.payment_provider_id
        partner = contract.partner_id
        partner.write({"firstname": "Jan", "lastname": "Kowalski Nowak"})
        with MockRequest(self.env, website=self.website):
            values = SponsorshipPayment._get_sponsorship_payment_values(
                contract, provider, "token", invoice
            )
            self.assertEqual(values["payu_gpo_cardholder_firstname"], "Jan")
            self.assertEqual(values["payu_gpo_cardholder_lastname"], "Kowalski Nowak")
            partner.my2_name_placeholder = True
            values = SponsorshipPayment._get_sponsorship_payment_values(
                contract, provider, "token", invoice
            )
            self.assertNotIn("payu_gpo_cardholder_firstname", values)

    def test_full_name_of_an_older_session_is_split(self):
        contract = self._make_digital_contract()
        with MockRequest(self.env, website=self.website) as request:
            request.session[CARDHOLDER_NAMES_SESSION_KEY] = {
                str(contract.id): "Anna Maria Nowak"
            }
            self.assertEqual(
                session_cardholder_names(CARDHOLDER_NAMES_SESSION_KEY),
                {str(contract.id): ["Anna Maria", "Nowak"]},
            )

    def test_no_name_kept_without_one(self):
        contract = self._make_digital_contract()
        with MockRequest(self.env, website=self.website) as request:
            wizard = self._wizard(payment_method=self.standing_order_mode.id)
            self.assertFalse(self._submit(request, wizard, contract))

    def test_card_form_prefilled_and_visible(self):
        html = str(
            self.env["ir.qweb"]._render(
                "payment_payu_gpo.inline_form",
                {
                    "provider_sudo": self.provider,
                    "pm_sudo": self.env.ref("payment.payment_method_card"),
                    "payu_gpo_cardholder_firstname": "Anna",
                    "payu_gpo_cardholder_lastname": "Nowak",
                },
            )
        )
        self.assertIn('value="Anna"', html)
        self.assertIn('value="Nowak"', html)
        self.assertNotIn("d-none", html)
