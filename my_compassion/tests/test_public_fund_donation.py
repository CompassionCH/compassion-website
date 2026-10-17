import re

from odoo.tests import tagged
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    HttpCase,
    JsonRpcException,
    Opener,
)

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


@tagged("post_install", "-at_install")
class TestPublicFundDonation(HttpCase):
    """A visitor gives to a fund without an account, over HTTP.

    Funds only (a gift goes to a sponsored child), once only, and the donor is
    asked their email alone before the payment, as in the sponsorship fast
    checkout: the name comes from the payment or from the thank-you page.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Host-based website resolution, as in TestFastCheckoutRoutes.
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        Product = cls.env["product.template"].with_company(cls.website.company_id)
        values = {
            "type": "service",
            "sale_ok": True,
            "list_price": 1.0,
            "activate_for_my_compassion": True,
            "my_compassion_donation_amount_low": 25.0,
            "my_compassion_donation_amount_medium": 50.0,
            "my_compassion_donation_amount_high": 100.0,
        }
        cls.fund = Product.create(
            {
                **values,
                "name": "Visitor Test Fund",
                "my_compassion_name": "Visitor Test Fund",
                "my_compassion_donation_type": "fund",
            }
        )
        cls.gift = Product.create(
            {
                **values,
                "name": "Visitor Test Gift",
                "my_compassion_name": "Visitor Test Gift",
                "my_compassion_donation_type": "gift",
            }
        )

    # === Helpers ===

    def _add_fund(self, **params):
        return self.make_jsonrpc_request(
            "/my2/gifts/new",
            {
                "product_id": self.fund.id,
                "suggested_amount": "medium",
                "frequency": "one_time",
                **params,
            },
        )

    def _cart(self):
        return self.env["sale.order"].search(
            [("website_id", "=", self.website.id)], order="id desc", limit=1
        )

    def _give_email(self, email="Donor@Example.org ", consent="on", change=False):
        page = self.url_open(
            "/my2/gift-package" + ("?change_donor=1" if change else "")
        )
        data = {"csrf_token": CSRF_RE.search(page.text).group(1), "email": email}
        if consent:
            data["privacy_consent"] = consent
        return self.url_open("/my2/gift-package/donor", data=data)

    # === Funds open, gifts closed ===

    def test_visitor_sees_funds_not_gifts(self):
        page = self.url_open("/my2/gifts")
        self.assertEqual(page.status_code, 200)
        self.assertIn(f"/my2/gifts/{self.fund.id}", page.text)
        self.assertNotIn(f"/my2/gifts/{self.gift.id}", page.text)

        gifts = self.url_open("/my2/gifts?type=gift", allow_redirects=False)
        self.assertEqual(gifts.status_code, 303)
        self.assertIn("/web/login", gifts.headers["Location"])

        fund_page = self.url_open(f"/my2/gifts/{self.fund.id}")
        self.assertEqual(fund_page.status_code, 200)
        gift_page = self.url_open(f"/my2/gifts/{self.gift.id}", allow_redirects=False)
        self.assertEqual(gift_page.status_code, 303)
        self.assertIn("/web/login", gift_page.headers["Location"])

    def test_visitor_cannot_add_a_gift(self):
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/my2/gifts/new",
                {
                    "product_id": self.gift.id,
                    "suggested_amount": "low",
                    "recipient": 1,
                },
            )

    def test_a_fund_not_published_for_the_company_is_refused(self):
        self.fund.with_company(
            self.website.company_id
        ).activate_for_my_compassion = False
        page = self.url_open(f"/my2/gifts/{self.fund.id}", allow_redirects=False)
        self.assertEqual(page.status_code, 303)
        with self.assertRaises(JsonRpcException):
            self._add_fund()

    def test_visitor_gives_once(self):
        self._add_fund(frequency="monthly")
        line = self._cart().order_line
        self.assertEqual(line.frequency, "one_time")
        self.assertEqual(line.price_unit, 50.0)

    # === The email step ===

    def test_no_partner_before_the_email_step(self):
        partners = self.env["res.partner"].search_count([])
        self._add_fund()
        cart = self._cart()
        self.assertEqual(cart.partner_id, self.website.partner_id)
        self.assertEqual(self.env["res.partner"].search_count([]), partners)

        page = self.url_open("/my2/gift-package")
        self.assertIn('action="/my2/gift-package/donor"', page.text)
        self.assertNotIn("o_payment_form", page.text)

    def test_email_step_creates_the_placeholder_donor(self):
        self._add_fund()
        response = self._give_email()
        self.assertEqual(response.status_code, 200)

        cart = self._cart()
        donor = cart.partner_id
        self.assertNotEqual(donor, self.website.partner_id)
        self.assertTrue(donor.my2_name_placeholder)
        self.assertEqual(donor.email, "donor@example.org")
        self.assertTrue(donor.legal_agreement_date)
        self.assertEqual(donor.country_id, self.website.company_id.country_id)
        self.assertEqual(cart.partner_invoice_id, donor)
        # The amount the donor chose survives the change of partner.
        self.assertEqual(cart.order_line.price_unit, 50.0)

        # Now the payment form, and the receipt address with a way to change it.
        self.assertNotIn('action="/my2/gift-package/donor"', response.text)
        self.assertIn("donor@example.org", response.text)

        # A new email updates the same donor, never creates a second one.
        partners = self.env["res.partner"].search_count([])
        self._give_email(email="other@example.org", change=True)
        self.assertEqual(self._cart().partner_id, donor)
        self.assertEqual(donor.email, "other@example.org")
        self.assertEqual(self.env["res.partner"].search_count([]), partners)

    def test_email_step_needs_consent_and_a_valid_email(self):
        self._add_fund()
        for email, consent in (("not-an-email", "on"), ("donor@example.org", None)):
            response = self._give_email(email=email, consent=consent)
            self.assertIn('action="/my2/gift-package/donor"', response.text)
            self.assertEqual(self._cart().partner_id, self.website.partner_id)

    # === The name, after the payment ===

    def test_thank_you_page_asks_the_name_once(self):
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        page = self.url_open("/my2/gifts/thankyou")
        self.assertIn('action="/my2/gifts/thankyou/details"', page.text)

        csrf = CSRF_RE.search(page.text).group(1)
        self.url_open(
            "/my2/gifts/thankyou/details",
            data={"csrf_token": csrf, "firstname": "Anna", "lastname": "Nowak"},
        )
        self.assertFalse(donor.my2_name_placeholder)
        self.assertEqual((donor.firstname, donor.lastname), ("Anna", "Nowak"))

        # A real name is never overwritten, and the form is gone.
        page = self.url_open("/my2/gifts/thankyou")
        self.assertNotIn('action="/my2/gifts/thankyou/details"', page.text)
        self.url_open(
            "/my2/gifts/thankyou/details",
            data={"csrf_token": csrf, "firstname": "Eve", "lastname": "Mallory"},
        )
        self.assertEqual((donor.firstname, donor.lastname), ("Anna", "Nowak"))

    def test_another_session_cannot_name_the_donor(self):
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            page = self.url_open("/my2/gifts")
            csrf = CSRF_RE.search(page.text)
            self.url_open(
                "/my2/gifts/thankyou/details",
                data={
                    "csrf_token": csrf.group(1) if csrf else "",
                    "firstname": "Eve",
                    "lastname": "Mallory",
                },
            )
        finally:
            self.opener = own_opener
        self.assertTrue(donor.my2_name_placeholder)

    # === No Odoo sales email for a donation ===

    def test_no_sales_email_for_a_my_compassion_order(self):
        self._add_fund()
        self._give_email()
        cart = self._cart().sudo()
        template = self.env.ref("sale.mail_template_sale_confirmation")
        messages = len(cart.message_ids)
        cart._send_order_notification_mail(template)
        self.assertEqual(len(cart.message_ids), messages)
