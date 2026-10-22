from unittest.mock import patch

from odoo import Command, fields
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
        cls.shared_fund = cls._product(
            "Fund Of Both Companies",
            (cls.website_company, cls.website_amounts),
            (cls.donor_company, cls.donor_amounts),
        )
        cls.website_fund = cls._product(
            "Fund Of The Website Company", (cls.website_company, cls.website_amounts)
        )
        cls.donor_fund = cls._product(
            "Fund Of The Donor Company", (cls.donor_company, cls.donor_amounts)
        )

        # A gift with giving limits, for the donor's sponsorship (in the
        # donor's company, as their contracts are).
        cls.gift = cls._product(
            "Gift Of The Website Company",
            (cls.website_company, cls.website_amounts),
            donation_type="gift",
        )
        gift_type = cls.env["sponsorship.gift.type"].create(
            {
                "name": "Website Company Gift",
                "code": "my2_website_company_gift",
                "product_id": cls.gift.id,
            }
        )
        cls.env["gift.threshold.settings"].create(
            {
                "gift_type_id": gift_type.id,
                "min_amount": 10.0,
                "max_amount": 200.0,
                "gift_frequency": 2,
                "yearly_threshold": True,
                "currency_id": cls.website_company.currency_id.id,
            }
        )
        partner = cls.donor.partner_id
        partner.country_id = cls.env.ref("base.ch")
        project = cls.env["compassion.project"].create(
            {"fcp_id": "donor_company_fcp", "last_update_date": fields.Date.today()}
        )
        child = cls.env["compassion.child"].create(
            {
                "name": "Donor Company Child",
                "global_id": "donor_company_child",
                "local_id": "DC1234567",
                "project_id": project.id,
            }
        )
        group = cls.env["recurring.contract.group"].create(
            {"partner_id": partner.id, "company_id": cls.donor_company.id}
        )
        line_product = cls.env["product.product"].create(
            {"name": "Sponsorship Line", "type": "service"}
        )
        pricelist = cls.env["product.pricelist"].search(
            [("company_id", "in", [False, cls.donor_company.id])], limit=1
        )
        # The hold of the child (a GMC exchange) is out of scope here.
        with patch.object(
            cls.registry["compassion.child"],
            "child_sponsored",
            lambda child, sponsor_id: None,
        ):
            cls.sponsorship = cls.env["recurring.contract"].create(
                {
                    "type": "S",
                    "child_id": child.id,
                    "partner_id": partner.id,
                    "correspondent_id": partner.id,
                    "group_id": group.id,
                    "company_id": cls.donor_company.id,
                    "pricelist_id": pricelist.id,
                    # A partner's sponsorships are found through their lines.
                    "contract_line_ids": [
                        Command.create({"product_id": line_product.id, "amount": 42.0})
                    ],
                }
            )

    @classmethod
    def _product(cls, name, *published, donation_type="fund", company=False):
        """A donation product, published by each company with its amounts."""
        product = cls.env["product.template"].create(
            {
                "name": name,
                "my_compassion_name": name,
                "type": "service",
                "sale_ok": True,
                "list_price": 1.0,
                "company_id": company and company.id,
                "my_compassion_donation_type": donation_type,
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
        self.assertEqual(
            self.make_jsonrpc_request(
                "/my2/gifts/get-limits", {"product_id": self.website_fund.id}
            ),
            {},
        )

        page = self.url_open(f"/my2/gifts/{self.donor_fund.id}")
        self.assertEqual(page.status_code, 404)
        with self.assertRaises(JsonRpcException):
            self._add(self.donor_fund)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/my2/gifts/get-limits", {"product_id": self.donor_fund.id}
            )

    def test_a_gift_with_giving_limits(self):
        page = self.url_open(f"/my2/gifts/{self.gift.id}")
        self.assertEqual(page.status_code, 200)
        self.assertRegex(page.text, rf'<option[^>]*value="{self.sponsorship.id}"')
        limits = self.make_jsonrpc_request(
            "/my2/gifts/get-limits",
            {"product_id": self.gift.id, "sponsorship_id": self.sponsorship.id},
        )
        self.assertEqual(
            limits, {"min_amount": 10.0, "max_amount": 200.0, "remaining_donations": 2}
        )

        self.make_jsonrpc_request(
            "/my2/gifts/new",
            {
                "product_id": self.gift.id,
                "suggested_amount": "medium",
                "recipient": self.sponsorship.id,
            },
        )
        line = (
            self.env["sale.order"]
            .search([("partner_id", "=", self.donor.partner_id.id)])
            .order_line
        )
        self.assertEqual(line.gift_recipient_id, self.sponsorship)
        self.assertEqual(line.price_unit, self.website_amounts[1])
