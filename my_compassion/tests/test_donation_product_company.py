from unittest.mock import patch

from odoo import Command, fields
from odoo.modules.migration import load_script
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

    def test_a_copy_keeps_the_suggested_amounts(self):
        self.product.write(
            {
                "activate_for_my_compassion": True,
                "my_compassion_donation_amount_low": 25.0,
                "my_compassion_donation_amount_medium": 60.0,
                "my_compassion_donation_amount_high": 120.0,
            }
        )
        copy = self.product.copy()
        self.assertEqual(
            (
                copy.activate_for_my_compassion,
                copy.my_compassion_donation_amount_low,
                copy.my_compassion_donation_amount_medium,
                copy.my_compassion_donation_amount_high,
            ),
            (False, 25.0, 60.0, 120.0),
        )

    def test_a_child_company_website_offers_its_parent_products(self):
        """A country office under a regional company (Sverige under Compassion
        Norden) gives to the products of its parent, not of a sibling."""
        parent = self.env["res.company"].create({"name": "Regional Company"})
        child, sibling = self.env["res.company"].create(
            [
                {"name": "Country Company", "parent_id": parent.id},
                {"name": "Sibling Company", "parent_id": parent.id},
            ]
        )
        website = self.env["website"].create(
            {"name": "Country MyCompassion", "company_id": child.id}
        )
        products = self.env["product.template"]
        for company in (parent, child, sibling):
            product = products.create(
                {
                    "name": f"Fund Of {company.name}",
                    "type": "service",
                    "my_compassion_donation_type": "fund",
                    "company_id": company.id,
                }
            )
            product.with_company(child).activate_for_my_compassion = True
            products |= product
        self.assertEqual(
            set(website._my2_donation_products([("id", "in", products.ids)])),
            set(products[:2]),
        )


@tagged("post_install", "-at_install")
class TestDonationProductPreMigration(TransactionCase):
    """The pre-migration to 18.0.1.0.29 turns the MyCompassion activation and
    suggested amounts into company-dependent (jsonb) columns."""

    COLUMNS = (
        "activate_for_my_compassion",
        "my_compassion_donation_amount_low",
        "my_compassion_donation_amount_medium",
        "my_compassion_donation_amount_high",
    )

    def _columns(self):
        self.env.cr.execute(
            """SELECT column_name, data_type, column_default
               FROM information_schema.columns
               WHERE table_name = 'product_template' AND column_name IN %s""",
            [self.COLUMNS],
        )
        return {name: (kind, default) for name, kind, default in self.env.cr.fetchall()}

    def test_the_values_go_to_the_product_company(self):
        main = self.env.ref("base.main_company")
        other = self.env["res.company"].create({"name": "Legacy Fund Company"})
        shared, own, empty = self.env["product.template"].create(
            [
                {"name": "Legacy Shared Fund", "type": "service"},
                {
                    "name": "Legacy Fund Of A Company",
                    "type": "service",
                    "company_id": other.id,
                },
                {"name": "Legacy Empty Fund", "type": "service"},
            ]
        )
        self.env.flush_all()
        cr = self.env.cr
        # The columns before: a boolean as the ORM creates it (DEFAULT false),
        # and numeric amounts.
        cr.execute(
            """ALTER TABLE product_template
               ALTER COLUMN activate_for_my_compassion TYPE boolean USING NULL,
               ALTER COLUMN activate_for_my_compassion SET DEFAULT false,
               ALTER COLUMN my_compassion_donation_amount_low TYPE numeric USING NULL,
               ALTER COLUMN my_compassion_donation_amount_medium
                   TYPE numeric USING NULL,
               ALTER COLUMN my_compassion_donation_amount_high TYPE numeric USING NULL
            """
        )
        for product, active, low in (
            (shared, True, 20),
            (own, True, 30),
            (empty, False, None),
        ):
            cr.execute(
                """UPDATE product_template
                   SET activate_for_my_compassion = %s,
                       my_compassion_donation_amount_low = %s
                   WHERE id = %s""",
                (active, low, product.id),
            )

        load_script(
            "my_compassion/migrations/18.0.1.0.29/pre-migration.py",
            "my_compassion_pre_migration_18_0_1_0_29",
        ).migrate(cr, "18.0.1.0.28")

        self.assertEqual(self._columns(), dict.fromkeys(self.COLUMNS, ("jsonb", None)))
        cr.execute(
            """SELECT activate_for_my_compassion, my_compassion_donation_amount_low,
                      my_compassion_donation_amount_medium
               FROM product_template WHERE id IN %s ORDER BY id""",
            [(shared.id, own.id, empty.id)],
        )
        self.assertEqual(
            cr.fetchall(),
            [
                ({str(main.id): True}, {str(main.id): 20}, None),
                ({str(other.id): True}, {str(other.id): 30}, None),
                (None, None, None),
            ],
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
        cls.french = cls.env["res.lang"]._activate_lang("fr_FR")
        cls.website.language_ids |= cls.french
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
        # Owned by the donor's company: the website's company cannot publish it.
        cls.foreign_fund = cls._product(
            "Fund Owned By The Donor Company",
            (cls.website_company, cls.website_amounts),
            company=cls.donor_company,
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

    def test_a_product_of_another_company(self):
        for url in ("/my2/gifts", "/my2/gift-package/add"):
            page = self.url_open(url)
            self.assertEqual(page.status_code, 200, url)
            self.assertNotIn("Fund Owned By The Donor Company", page.text, url)
        page = self.url_open(f"/my2/gifts/{self.foreign_fund.id}")
        self.assertEqual(page.status_code, 404)
        with self.assertRaises(JsonRpcException):
            self._add(self.foreign_fund)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/my2/gifts/get-limits", {"product_id": self.foreign_fund.id}
            )

    def test_old_slugged_links(self):
        """Links with the product's slug lead to the details page, with their
        language and query string."""
        page = self.url_open(f"/my2/gifts/{self.shared_fund.id}")
        self.assertEqual(page.status_code, 200)

        page = self.url_open(
            f"/my2/gifts/fund-of-both-companies-{self.shared_fund.id}",
            allow_redirects=False,
        )
        self.assertEqual(page.status_code, 301)
        self.assertTrue(
            page.headers["Location"].endswith(f"/my2/gifts/{self.shared_fund.id}")
        )

        page = self.url_open(
            f"/my2/gifts/fund-of-the-donor-company-{self.donor_fund.id}",
            allow_redirects=False,
        )
        self.assertEqual(page.status_code, 404)

        # Last: the session then prefers French.
        lang = self.french.url_code
        page = self.url_open(
            f"/{lang}/my2/gifts/fund-of-both-companies-{self.shared_fund.id}"
            "?utm_source=newsletter",
            allow_redirects=False,
        )
        self.assertEqual(page.status_code, 301)
        self.assertTrue(
            page.headers["Location"].endswith(
                f"/{lang}/my2/gifts/{self.shared_fund.id}?utm_source=newsletter"
            ),
            page.headers["Location"],
        )

    def test_an_old_slugged_link_signed_out(self):
        """The slugged link leads to the details page, which asks a signed-out
        visitor to log in."""
        self.authenticate(None, None)
        page = self.url_open(
            f"/my2/gifts/gift-of-the-website-company-{self.gift.id}",
            allow_redirects=False,
        )
        self.assertEqual(page.status_code, 301)
        self.assertTrue(page.headers["Location"].endswith(f"/my2/gifts/{self.gift.id}"))
        page = self.url_open(page.headers["Location"], allow_redirects=False)
        self.assertIn(page.status_code, (302, 303))
        self.assertIn("/web/login", page.headers["Location"])
