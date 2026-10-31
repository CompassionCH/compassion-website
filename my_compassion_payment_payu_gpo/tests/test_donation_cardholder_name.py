import re

from odoo import Command
from odoo.tests import HttpCase, tagged

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
NAME_INPUT_RE = re.compile(r'<input[^>]*name="cardholder_(?:first|last)name"[^>]*>')


@tagged("post_install", "-at_install")
class TestDonationCardholderName(HttpCase):
    """The email step of a visitor's donation asks the first and last name on
    the card when the website offers PayU, as the sponsorship fast checkout
    does."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        company = cls.website.company_id
        cls.fund = (
            cls.env["product.template"]
            .with_company(company)
            .create(
                {
                    "type": "service",
                    "sale_ok": True,
                    "list_price": 1.0,
                    "activate_for_my_compassion": True,
                    "my_compassion_donation_amount_low": 25.0,
                    "my_compassion_donation_amount_medium": 50.0,
                    "my_compassion_donation_amount_high": 100.0,
                    "name": "Cardholder Test Fund",
                    "my_compassion_name": "Cardholder Test Fund",
                    "my_compassion_donation_type": "fund",
                }
            )
        )
        cls.other_providers = cls.env["payment.provider"].search(
            [
                ("company_id", "=", company.id),
                ("state", "in", ("enabled", "test")),
                ("is_published", "=", True),
            ]
        )
        cls.payu = cls.env["payment.provider"].create(
            {
                "name": "Cardholder Test PayU",
                "code": "payu_gpo",
                "company_id": company.id,
                "state": "test",
                "is_published": True,
                "payu_gpo_pos_id": "300746",
                "payu_gpo_client_id": "300746",
                "payu_gpo_client_secret": "test-client-secret",
                "payu_gpo_second_key": "test-second-key",
                "payment_method_ids": [
                    Command.link(cls.env.ref("payment.payment_method_card").id)
                ],
            }
        )

    def _payu_only(self):
        self.other_providers.state = "disabled"

    def _add_fund(self):
        return self.make_jsonrpc_request(
            "/my2/gifts/new",
            {
                "product_id": self.fund.id,
                "suggested_amount": "medium",
                "frequency": "one_time",
            },
        )

    def _cart(self):
        return self.env["sale.order"].search(
            [("website_id", "=", self.website.id)], order="id desc", limit=1
        )

    def _name_inputs(self, url="/my2/gift-package"):
        return NAME_INPUT_RE.findall(self.url_open(url).text)

    def _give_email(self, names=None, change=False):
        page = self.url_open(
            "/my2/gift-package" + ("?change_donor=1" if change else "")
        )
        data = {
            "csrf_token": CSRF_RE.search(page.text).group(1),
            "email": "donor@example.org",
            "privacy_consent": "on",
        }
        if names is not None:
            data["cardholder_firstname"], data["cardholder_lastname"] = names
        return self.url_open("/my2/gift-package/donor", data=data)

    def test_required_when_payu_is_the_only_provider(self):
        self._payu_only()
        self._add_fund()
        inputs = self._name_inputs()
        self.assertEqual(len(inputs), 2)
        self.assertTrue(all("required" in field for field in inputs))

        response = self._give_email(names=("Anna", "  "))
        self.assertIn("donor_error=cardholder", response.url)
        self.assertIn(
            "Please enter the first and last name on the card.", response.text
        )
        self.assertEqual(self._cart().partner_id, self.website.partner_id)

        self._give_email(names=("  Anna ", " Maria   Nowak"))
        self.assertTrue(self._cart().partner_id.my2_name_placeholder)
        # Kept for the card form, and shown again to change the email.
        firstname, lastname = self._name_inputs("/my2/gift-package?change_donor=1")
        self.assertIn('value="Anna"', firstname)
        self.assertIn('value="Maria Nowak"', lastname)

    def test_optional_next_to_another_provider(self):
        self._payu_only()
        self.env["payment.provider"].create(
            {
                "name": "Cardholder Test Other",
                "code": "none",
                "company_id": self.website.company_id.id,
                "state": "test",
                "is_published": True,
            }
        )
        self._add_fund()
        inputs = self._name_inputs()
        self.assertEqual(len(inputs), 2)
        self.assertFalse(any("required" in field for field in inputs))
        self._give_email()
        self.assertTrue(self._cart().partner_id.my2_name_placeholder)

    def test_not_asked_without_payu(self):
        self.payu.state = "disabled"
        self._add_fund()
        self.assertFalse(self._name_inputs())
