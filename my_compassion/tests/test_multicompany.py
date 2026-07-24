from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools.misc import hmac as hmac_tool

from ..models.contract_group import UPDATE_CARD_TOKEN_SCOPE
from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestMultiCompany(DigitalSeamCase):
    """Multi-company hardening of the digital payment seam.

    Each country company runs its own website. A signup, a saved token, an
    off-session charge and a signed update-card link must all stay inside
    the company they belong to and never bleed into a sibling company.
    """

    def _two_sale_companies(self):
        """Return two distinct companies that both have sale accounting.

        The batch tests bill real companies (Sverige, Norge, ...) but only
        add rolled-back records to them, so no company config is mutated.
        """
        companies = self.env["account.journal"].search(
            [("type", "=", "sale")]
        ).company_id
        self.assertGreaterEqual(
            len(companies), 2, "the database needs two companies with sale accounting"
        )
        return companies[0], companies[1]

    def test_finish_sponsorship_uses_website_company(self):
        # The wizard carries the website's company. The new contract and its
        # collection group must land in that company, not in the operator's
        # default company.
        website_company = self.env["res.company"].create(
            {"name": "Multi Co Website"}
        )
        self.assertNotEqual(website_company, self.env.company)
        provider = self.env["payment.provider"].create(
            {
                "name": "Multi Co Provider",
                "code": "none",
                "company_id": website_company.id,
                "state": "test",
            }
        )
        mode = self.env["account.payment.mode"].create(
            {
                "name": "Multi Co Mode",
                "company_id": website_company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": provider.id,
            }
        )
        mode.is_published = True
        child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(child, "the database needs a child")
        wizard = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": self.env.ref("base.public_user").id,
                "child_id": child.id,
                "company_id": website_company.id,
                "payment_method": mode.id,
                "sponsorship_plus": True,
                "firstname": "Multi",
                "lastname": "Company",
                "email": "multi-company-signup@example.com",
                # the partner needs a country so the contract's required
                # country_id computes
                "country": self.env.ref("base.se").id,
            }
        )
        product = self.env["product.product"].search(
            [("default_code", "=", "sponsorship")], limit=1
        )

        def fake_lines(contract_self, correspondence):
            return [
                Command.clear(),
                Command.create(
                    {"product_id": product.id, "amount": 100, "quantity": 1}
                ),
            ]

        # child_sponsored drives the GMC hold state and is out of scope here.
        # the standard line builder needs a fully configured company, which
        # this throwaway one is not, so it is stubbed with a plain line.
        with patch.object(
            self.registry["compassion.child"],
            "child_sponsored",
            lambda child_self, sponsor_id: None,
        ), patch.object(
            self.registry["recurring.contract"],
            "_get_sponsorship_standard_lines",
            fake_lines,
        ):
            sponsorship = wizard.finish_sponsorship()
        self.assertEqual(sponsorship.company_id, website_company)
        self.assertEqual(sponsorship.group_id.company_id, website_company)
        self.assertEqual(sponsorship.group_id.payment_mode_id, mode)
        self.assertEqual(sponsorship.payment_mode_id.company_id, website_company)

    def _finish_logged_in_signup(self, partner, website_company):
        """Run a logged-in standard signup for partner on website_company.

        The throwaway website company has no sale accounting, so the child
        hold and the standard line builder are stubbed the same way the
        public-signup test does, leaving only the country handling under
        test.
        """
        user = self.env["res.users"].create(
            {
                "name": partner.name,
                "login": f"signup-{partner.id}@example.com",
                "partner_id": partner.id,
                "groups_id": [Command.set([self.env.ref("base.group_portal").id])],
            }
        )
        self.assertFalse(user._is_public())
        child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(child, "the database needs a child")
        wizard = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": user.id,
                "child_id": child.id,
                "company_id": website_company.id,
            }
        )
        product = self.env["product.product"].search(
            [("default_code", "=", "sponsorship")], limit=1
        )

        def fake_lines(contract_self, correspondence):
            return [
                Command.clear(),
                Command.create(
                    {"product_id": product.id, "amount": 100, "quantity": 1}
                ),
            ]

        with patch.object(
            self.registry["compassion.child"],
            "child_sponsored",
            lambda child_self, sponsor_id: None,
        ), patch.object(
            self.registry["recurring.contract"],
            "_get_sponsorship_standard_lines",
            fake_lines,
        ):
            return wizard.finish_sponsorship()

    def test_finish_logged_in_partner_without_country_uses_company(self):
        # A logged-in sponsor with no country on file must not crash the
        # required country_id of the contract. The wizard backfills the
        # website company country onto the sponsor so the contract computes.
        website_company = self.env["res.company"].create(
            {"name": "Country Fallback Co"}
        )
        website_company.partner_id.country_id = self.env.ref("base.se")
        partner = self.env["res.partner"].create({"name": "Sponsor No Country"})
        self.assertFalse(partner.country_id)
        sponsorship = self._finish_logged_in_signup(partner, website_company)
        self.assertEqual(sponsorship.country_id, self.env.ref("base.se"))
        self.assertEqual(partner.country_id, self.env.ref("base.se"))

    def test_finish_logged_in_partner_keeps_own_country(self):
        # A logged-in sponsor who already has a country keeps it. The
        # website company country never overrides the sponsor's own.
        website_company = self.env["res.company"].create(
            {"name": "Own Country Co"}
        )
        website_company.partner_id.country_id = self.env.ref("base.se")
        partner = self.env["res.partner"].create(
            {"name": "Sponsor Norway", "country_id": self.env.ref("base.no").id}
        )
        sponsorship = self._finish_logged_in_signup(partner, website_company)
        self.assertEqual(sponsorship.country_id, self.env.ref("base.no"))
        self.assertEqual(partner.country_id, self.env.ref("base.no"))

    def test_token_constraint_rejects_cross_sponsor(self):
        # Same company as the group, but the token belongs to a different
        # sponsor. The group constraint must reject it just like it rejects a
        # foreign-company token.
        provider = self.env["payment.provider"].create(
            {
                "name": "Cross Sponsor Provider",
                "code": "none",
                "company_id": self.company.id,
            }
        )
        other_partner = self.env["res.partner"].create(
            {"name": "Cross Sponsor Other"}
        )
        method = self.env["payment.method"].search([], limit=1)
        token = self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": other_partner.id,
                "provider_ref": "cross-sponsor-ref",
                "payment_details": "5678",
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            self.partner, self.company, self.mode
        )
        # token company matches, sponsor does not -> rejected
        self.assertEqual(token.company_id, group.company_id)
        with self.assertRaises(ValidationError):
            group.payment_token_id = token

    def test_cron_charges_each_company_under_its_own(self):
        # One batch spanning two companies charges each invoice against its
        # own company's provider and token, and every transaction lands in
        # the company of its group.
        company_a, company_b = self._two_sale_companies()
        contract_a, invoice_a, token_a = self._make_chargeable_invoice(
            company=company_a
        )
        contract_b, invoice_b, token_b = self._make_chargeable_invoice(
            company=company_b
        )
        self.assertNotEqual(company_a, company_b)
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        tx_a = self.env["payment.transaction"].search(
            [("invoice_ids", "in", invoice_a.ids)]
        )
        tx_b = self.env["payment.transaction"].search(
            [("invoice_ids", "in", invoice_b.ids)]
        )
        self.assertEqual(len(tx_a), 1)
        self.assertEqual(len(tx_b), 1)
        self.assertEqual(tx_a.company_id, company_a)
        self.assertEqual(tx_b.company_id, company_b)
        self.assertEqual(
            tx_a.provider_id, contract_a.payment_mode_id.payment_provider_id
        )
        self.assertEqual(
            tx_b.provider_id, contract_b.payment_mode_id.payment_provider_id
        )
        self.assertEqual(tx_a.provider_id.company_id, company_a)
        self.assertEqual(tx_b.provider_id.company_id, company_b)
        self.assertEqual(tx_a.token_id, token_a)
        self.assertEqual(tx_b.token_id, token_b)
        # each cross-check: the group, token and invoice of a charge share
        # the transaction's company
        self.assertEqual(token_a.company_id, company_a)
        self.assertEqual(invoice_a.company_id, company_a)
        self.assertEqual(contract_a.group_id.company_id, company_a)

    def test_update_card_link_is_company_scoped(self):
        # Each company signs its own update-card link. A link minted for a
        # group in one company must not authenticate a sibling company's
        # group.
        company_a, company_b = self._two_sale_companies()
        partner_a = self.env["res.partner"].create({"name": "Link Sponsor A"})
        partner_b = self.env["res.partner"].create({"name": "Link Sponsor B"})
        Group = self.env["recurring.contract.group"]
        empty_mode = self.env["account.payment.mode"]
        group_a = Group._find_or_create_group(partner_a, company_a, empty_mode)
        group_b = Group._find_or_create_group(partner_b, company_b, empty_mode)
        url_a = group_a._my2_update_card_url()
        self.assertIn(f"group_id={group_a.id}", url_a)
        token_a = url_a.rsplit("access_token=", 1)[1]
        # the token authenticates its own group
        expected_a = hmac_tool(
            self.env(su=True),
            "generate_access_token",
            f"{UPDATE_CARD_TOKEN_SCOPE}|{group_a.id}|{group_a.partner_id.id}",
        )
        self.assertEqual(token_a, expected_a)
        # the very same token does not match the other company's group, so
        # the controller check_access_token would fail on it
        foreign = hmac_tool(
            self.env(su=True),
            "generate_access_token",
            f"{UPDATE_CARD_TOKEN_SCOPE}|{group_b.id}|{group_b.partner_id.id}",
        )
        self.assertNotEqual(token_a, foreign)
        token_b = group_b._my2_update_card_url().rsplit("access_token=", 1)[1]
        self.assertNotEqual(token_a, token_b)
