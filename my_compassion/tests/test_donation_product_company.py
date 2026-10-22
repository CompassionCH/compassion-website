from odoo import Command
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tests.common import JsonRpcException


@tagged("post_install", "-at_install")
class TestDonationProductCompany(TransactionCase):
    """Funds and gifts are shared products: each company publishes them on its
    own MyCompassion website, with its own amounts, in its own currency."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        pln = cls.env.ref("base.PLN")
        pln.active = True
        cls.company_b = cls.env["res.company"].create(
            {"name": "Donation Company B", "currency_id": pln.id}
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Shared Test Fund",
                "type": "service",
                "my_compassion_donation_type": "fund",
                "company_id": False,
            }
        )

    def _settings(self, company):
        product = self.product.with_company(company)
        return (
            product.activate_for_my_compassion,
            product.my_compassion_donation_amount_low,
            product.my_compassion_donation_amount_medium,
            product.my_compassion_donation_amount_high,
        )

    def test_every_company_starts_from_the_same_suggestions(self):
        for company in (self.company_a, self.company_b):
            self.assertEqual(self._settings(company), (False, 15.0, 50.0, 100.0))

    def test_each_company_has_its_own_settings(self):
        self.product.with_company(self.company_a).write(
            {
                "activate_for_my_compassion": True,
                "my_compassion_donation_amount_low": 25.0,
                "my_compassion_donation_amount_medium": 50.0,
                "my_compassion_donation_amount_high": 100.0,
            }
        )
        # The other company does not publish it, and keeps the defaults.
        self.assertEqual(self._settings(self.company_b), (False, 15.0, 50.0, 100.0))

        self.product.with_company(self.company_b).write(
            {
                "activate_for_my_compassion": True,
                "my_compassion_donation_amount_low": 80.0,
                "my_compassion_donation_amount_medium": 200.0,
                "my_compassion_donation_amount_high": 400.0,
            }
        )
        self.assertEqual(self._settings(self.company_b), (True, 80.0, 200.0, 400.0))
        # Back to the first company: its settings are untouched.
        self.assertEqual(self._settings(self.company_a), (True, 25.0, 50.0, 100.0))

        self.product.with_company(self.company_a).activate_for_my_compassion = False
        self.assertFalse(self._settings(self.company_a)[0])
        self.assertTrue(self._settings(self.company_b)[0])

    def test_amounts_in_the_currency_of_the_company(self):
        self.assertEqual(
            self.product.with_company(self.company_a).my_compassion_currency_id,
            self.company_a.currency_id,
        )
        self.assertEqual(
            self.product.with_company(self.company_b).my_compassion_currency_id,
            self.company_b.currency_id,
        )


@tagged("post_install", "-at_install")
class TestDonationProductWebsiteCompany(HttpCase):
    """A donor whose company is not the website's one (a Swiss donor on the
    Polish website) gives to what the website's company publishes, at its
    amounts and in its currency, as the cart is in that company."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Host-based website resolution, as in TestFastCheckoutRoutes.
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        cls.website_company = cls.website.company_id
        currency = cls.env.ref("base.PLN")
        if currency == cls.website_company.currency_id:
            currency = cls.env.ref("base.EUR")
        currency.active = True
        cls.donor_company = cls.env["res.company"].create(
            {"name": "Donor's Own Company", "currency_id": currency.id}
        )
        cls.donor = cls.env["res.users"].create(
            {
                "name": "Donor Of Another Company",
                "login": "donor-of-another-company",
                "password": "donor-of-another-company",
                "company_id": cls.donor_company.id,
                "company_ids": [Command.set(cls.donor_company.ids)],
                "groups_id": [Command.set([cls.env.ref("base.group_portal").id])],
            }
        )

        cls.website_amounts = (37.0, 73.0, 137.0)
        cls.donor_amounts = (81.0, 203.0, 401.0)
        cls.shared_fund = cls._fund(
            "Fund Of Both Companies",
            (cls.website_company, cls.website_amounts),
            (cls.donor_company, cls.donor_amounts),
        )
        cls.website_fund = cls._fund(
            "Fund Of The Website Company", (cls.website_company, cls.website_amounts)
        )
        cls.donor_fund = cls._fund(
            "Fund Of The Donor Company", (cls.donor_company, cls.donor_amounts)
        )

    @classmethod
    def _fund(cls, name, *published):
        """A shared fund, published by each company with its amounts."""
        product = cls.env["product.template"].create(
            {
                "name": name,
                "my_compassion_name": name,
                "type": "service",
                "sale_ok": True,
                "list_price": 1.0,
                "company_id": False,
                "my_compassion_donation_type": "fund",
            }
        )
        for company, (low, medium, high) in published:
            product.with_company(company).write(
                {
                    "activate_for_my_compassion": True,
                    "my_compassion_donation_amount_low": low,
                    "my_compassion_donation_amount_medium": medium,
                    "my_compassion_donation_amount_high": high,
                }
            )
        return product

    def setUp(self):
        super().setUp()
        self.authenticate(self.donor.login, self.donor.login)

    def _add(self, product, amount="low"):
        return self.make_jsonrpc_request(
            "/my2/gifts/new",
            {
                "product_id": product.id,
                "suggested_amount": amount,
                "frequency": "one_time",
            },
        )

    def test_the_pages_list_what_the_website_company_publishes(self):
        for url in ("/my2/gifts", "/my2/gift-package/add"):
            page = self.url_open(url)
            self.assertEqual(page.status_code, 200, url)
            self.assertIn("Fund Of Both Companies", page.text, url)
            self.assertIn("Fund Of The Website Company", page.text, url)
            self.assertNotIn("Fund Of The Donor Company", page.text, url)

    def test_the_amounts_and_currency_of_the_website_company(self):
        page = self.url_open(f"/my2/gifts/{self.shared_fund.id}")
        self.assertEqual(page.status_code, 200)
        currency = self.website_company.currency_id.name
        for amount in self.website_amounts:
            self.assertRegex(page.text, rf"{currency}\s*{amount:g}\b")
        self.assertNotIn(self.donor_company.currency_id.name, page.text)

        self._add(self.shared_fund, "low")
        self._add(self.website_fund, "high")
        cart = self.env["sale.order"].search(
            [("partner_id", "=", self.donor.partner_id.id)]
        )
        self.assertEqual(cart.company_id, self.website_company)
        self.assertEqual(
            sorted(cart.order_line.mapped("price_unit")),
            [self.website_amounts[0], self.website_amounts[2]],
        )

    def test_the_website_company_decides_what_is_published(self):
        page = self.url_open(f"/my2/gifts/{self.website_fund.id}")
        self.assertEqual(page.status_code, 200)
        # A fund has no gift limit, only the website's minimum.
        self.assertEqual(
            self.make_jsonrpc_request(
                "/my2/gifts/get-limits", {"product_id": self.website_fund.id}
            ),
            {"min_amount": self.website.my2_min_donation_amount},
        )

        page = self.url_open(f"/my2/gifts/{self.donor_fund.id}")
        self.assertEqual(page.status_code, 404)
        with self.assertRaises(JsonRpcException):
            self._add(self.donor_fund)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/my2/gifts/get-limits", {"product_id": self.donor_fund.id}
            )
