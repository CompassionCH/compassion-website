import base64
import re
import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlparse
from uuid import uuid4

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api, fields, http
from odoo.exceptions import UserError
from odoo.modules.migration import load_script
from odoo.tests import tagged
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    HttpCase,
    JsonRpcException,
    Opener,
    TransactionCase,
)
from odoo.tools import config

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
# The refusal of a payment while another one of the order may succeed.
ALREADY_PAID = (
    "This donation is already paid, or its payment is still under way. Please"
    " wait for its outcome, or check with your bank, before paying again."
)


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

    def test_minimum_donation_to_a_fund(self):
        """Card testers try stolen cards with tiny amounts."""
        self.website.my2_min_donation_amount = 10.0
        limits = self.make_jsonrpc_request(
            "/my2/gifts/get-limits", {"product_id": self.fund.id}
        )
        self.assertEqual(limits["min_amount"], 10.0)
        with self.assertRaises(JsonRpcException):
            self._add_fund(suggested_amount="custom", custom_amount="1")
        self._add_fund(suggested_amount="custom", custom_amount="10")
        self.assertEqual(self._cart().order_line.price_unit, 10.0)

    def _small_suggestions(self, minimum=5.0):
        """Suggestions of 1, 3 and 5 (as the Swiss Medical Assistance fund)
        and a minimum for visitors."""
        self.fund.with_company(self.website.company_id).write(
            {
                "my_compassion_donation_amount_low": 1.0,
                "my_compassion_donation_amount_medium": 3.0,
                "my_compassion_donation_amount_high": 5.0,
            }
        )
        self.website.my2_min_donation_amount = minimum

    def test_visitor_is_offered_only_amounts_from_the_minimum(self):
        self._small_suggestions()
        page = self.url_open(f"/my2/gifts/{self.fund.id}").text
        self.assertNotIn("-suggested-low", page)
        self.assertNotIn("-suggested-medium", page)
        self.assertRegex(page, r'-suggested-high"[^>]*data-amount="5.0"[^>]*checked')
        self._add_fund(suggested_amount="high")
        self.assertEqual(self._cart().order_line.price_unit, 5.0)
        # No suggestion reaches the minimum: the own amount, filled with it.
        self.website.my2_min_donation_amount = 10.0
        page = self.url_open(f"/my2/gifts/{self.fund.id}").text
        self.assertNotIn("-suggested-high", page)
        self.assertRegex(page, r'-suggested-custom"[^>]*checked')
        self.assertRegex(page, r'id="custom-amount"[^>]*value="10"')

    def test_visitor_below_the_minimum_is_told_why(self):
        self._small_suggestions()
        message = "The smallest donation to this fund is"
        limits = self.make_jsonrpc_request(
            "/my2/gifts/get-limits", {"product_id": self.fund.id}
        )
        self.assertEqual(limits["min_amount"], 5.0)
        self.assertIn(message, limits["min_amount_message"])
        self._assert_refused(
            "/my2/gifts/new",
            {
                "product_id": self.fund.id,
                "suggested_amount": "low",
                "frequency": "one_time",
            },
            message,
        )
        self.assertFalse(
            self.env["sale.order.line"].search(
                [("product_id.product_tmpl_id", "=", self.fund.id)]
            )
        )
        page = self.url_open(f"/my2/gifts/{self.fund.id}").text
        self.assertIn("donation-refusal-message", page)

    def test_logged_in_donor_gives_any_suggested_amount(self):
        """The minimum keeps card testers off the public form: a donor with
        an account gives every amount the fund suggests."""
        self._small_suggestions()
        self._portal_user("small-giver@example.org")
        page = self.url_open(f"/my2/gifts/{self.fund.id}").text
        self.assertRegex(page, r'-suggested-low"[^>]*data-amount="1.0"[^>]*checked')
        self._add_fund(suggested_amount="low")
        self.assertEqual(self._cart().order_line.price_unit, 1.0)

    def test_account_gives_a_custom_amount_from_the_lowest_suggestion(self):
        """Signup is open: a donor with an account chooses every suggestion,
        but no custom amount below the smaller of the website's minimum and
        the fund's lowest suggestion."""
        self._small_suggestions()
        self._portal_user("custom-giver@example.org")
        limits = self.make_jsonrpc_request(
            "/my2/gifts/get-limits", {"product_id": self.fund.id}
        )
        self.assertEqual(limits["min_amount"], 1.0)
        self._assert_refused(
            "/my2/gifts/new",
            {
                "product_id": self.fund.id,
                "suggested_amount": "custom",
                "custom_amount": "0.5",
                "frequency": "one_time",
            },
            "The smallest donation to this fund is",
        )
        self._add_fund(suggested_amount="custom", custom_amount="1")
        self.assertEqual(self._cart().order_line.price_unit, 1.0)

    def test_gift_is_offered_only_amounts_within_its_limits(self):
        """A gift's suggestions outside its limits (gift.threshold.settings,
        in the currency of the website's company) were offered, then
        refused."""
        gift_type = self.env["sponsorship.gift.type"].create(
            {"name": "Visitor Test Gift Type", "code": "VTGT"}
        )
        self.gift.sponsorship_gift_type_id = gift_type
        self.env["gift.threshold.settings"].create(
            {
                "gift_type_id": gift_type.id,
                "min_amount": 30.0,
                "max_amount": 80.0,
                "currency_id": self.website.company_id.currency_id.id,
            }
        )
        self._portal_user("gift-giver@example.org")
        page = self.url_open(f"/my2/gifts/{self.gift.id}").text
        self.assertNotIn("-suggested-low", page)
        self.assertNotIn("-suggested-high", page)
        self.assertRegex(page, r'-suggested-medium"[^>]*data-amount="50.0"[^>]*checked')

    def test_product_card_shows_the_lowest_amount_offered(self):
        """The fund's card on the add page says "From" the lowest amount its
        form offers: for a visitor, not a suggestion below the minimum."""
        self._small_suggestions()
        page = self.url_open("/my2/gift-package/add").text
        lowest = re.search(
            rf'href="/my2/gifts/{self.fund.id}"[\s\S]*?From[\s\S]*?([0-9.]+)\.-', page
        )
        self.assertEqual(lowest.group(1), "5")

    def test_cart_of_another_website_is_not_taken(self):
        """/my2 resolves to MyCompassion on any domain, while the session's
        cart may have been started on another website of that domain."""
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_cart = self.env["sale.order"].create(
            {
                "partner_id": other_website.partner_id.id,
                "website_id": other_website.id,
                "company_id": other_website.company_id.id,
            }
        )
        # A session the server keeps (a page alone does not store it).
        self._add_fund()
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session["sale_order_id"] = other_cart.id
        http.root.session_store.save(session)
        self._add_fund()
        cart = self._cart()
        self.assertNotEqual(cart, other_cart)
        self.assertEqual(cart.website_id, self.website)
        self.assertFalse(other_cart.order_line)

    def _shop_product(self):
        """A product the shop of every website sells, under the fund minimum."""
        return self.env["product.product"].create(
            {
                "name": "Shop Bookmark",
                "type": "service",
                "sale_ok": True,
                "list_price": 1.0,
                "is_published": True,
            }
        )

    def test_another_website_never_takes_the_cart(self):
        """The session is shared by the websites of a domain: the
        MyCompassion cart is never the cart of another one (the shop,
        crowdfunding, events), which starts its own."""
        self._add_fund()
        cart = self._cart()
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        product = self._shop_product()
        # Another host, the same session: requests files cookies under the
        # Host header, so the session cookie is sent explicitly.
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        self.make_jsonrpc_request(
            "/shop/cart/update_json",
            {"product_id": product.id, "add_qty": 1},
            headers={"Host": "other.example.org", "Cookie": cookies},
        )
        self.assertEqual(cart.order_line.product_id, self.fund.product_variant_id)
        other_cart = self.env["sale.order"].search(
            [("website_id", "=", other_website.id)], order="id desc", limit=1
        )
        self.assertNotEqual(other_cart, cart)
        self.assertEqual(other_cart.order_line.product_id, product)

    def test_abandoned_cart_revival_never_crosses_websites(self):
        """website_sale's abandoned-cart link (/shop/cart?access_token=...
        &revive=merge) moves the lines of the abandoned order into the cart
        of the session and cancels it: never between a MyCompassion order
        and a cart of another website."""
        self._add_fund()
        cart = self._cart()
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        headers = {"Host": "other.example.org", "Cookie": cookies}
        product = self._shop_product()
        self.make_jsonrpc_request(
            "/shop/cart/update_json",
            {"product_id": product.id, "add_qty": 1},
            headers=dict(headers),
        )
        shop_cart = self.env["sale.order"].search(
            [("website_id", "=", other_website.id)], order="id desc", limit=1
        )
        self.url_open(
            f"/shop/cart?access_token={cart._portal_ensure_token()}&revive=merge",
            headers=headers,
            allow_redirects=False,
        )
        self.assertEqual(cart.state, "draft")
        self.assertEqual(cart.order_line.product_id, self.fund.product_variant_id)
        self.assertEqual(shop_cart.order_line.product_id, product)

    def test_another_website_page_keeps_the_basket(self):
        """A page of another website that only reads the cart leaves the
        MyCompassion basket in the session: back on /my2, it is there."""
        self._add_fund()
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        page = self.url_open(
            "/shop/cart", headers={"Host": "other.example.org", "Cookie": cookies}
        )
        self.assertEqual(page.status_code, 200)
        page = self.url_open("/my2/gift-package")
        self.assertIn("Visitor Test Fund", page.text)

    def test_shop_order_revival_never_reaches_the_basket(self):
        """On another website, the MyCompassion basket kept for the visitor's
        return is not the cart website_sale's abandoned-cart link merges
        into: a shop order revived there stays a shop order."""
        self._add_fund()
        cart = self._cart()
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        product = self._shop_product()
        shop_order = self.env["sale.order"].create(
            {
                "partner_id": other_website.partner_id.id,
                "website_id": other_website.id,
                "company_id": other_website.company_id.id,
                "order_line": [(0, 0, {"product_id": product.id})],
            }
        )
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        self.url_open(
            f"/shop/cart?access_token={shop_order._portal_ensure_token()}&revive=merge",
            headers={"Host": "other.example.org", "Cookie": cookies},
            allow_redirects=False,
        )
        self.assertEqual(cart.order_line.product_id, self.fund.product_variant_id)
        self.assertEqual(shop_order.state, "draft")
        self.assertEqual(shop_order.order_line.product_id, product)
        page = self.url_open("/my2/gift-package")
        self.assertIn("Visitor Test Fund", page.text)

    def test_shop_routes_never_add_to_the_cart(self):
        """Only the gift package's routes change a MyCompassion cart: a shop
        product priced under the fund minimum would get around it."""
        self._add_fund()
        cart = self._cart()
        product = self._shop_product()
        self._assert_refused(
            "/shop/cart/update_json",
            {"product_id": product.id, "add_qty": 1},
            "Please add and change your donations in your gift package.",
        )
        self.assertEqual(cart.order_line.product_id, self.fund.product_variant_id)

    def test_no_express_checkout_for_a_my_compassion_cart(self):
        """website_sale's cart page holds an express payment form (with the
        cart's access token), and its express routes set the cart's partners
        without the email step."""
        self._add_fund()
        cart = self._cart()
        address = {
            "name": "Eve Mallory",
            "email": "eve@example.org",
            "street": "Rue du Test 1",
            "city": "Lausanne",
            "zip": "1000",
            "country": "CH",
        }
        for route, params in (
            ("/shop/express_checkout", {"billing_address": address}),
            (
                "/shop/express/shipping_address_change",
                {"partial_delivery_address": address},
            ),
        ):
            self._assert_refused(
                route, params, "Please pay your donation from your gift package."
            )
        self.assertEqual(cart.partner_id, self.website.partner_id)
        self.assertEqual(cart.partner_invoice_id, self.website.partner_id)
        page = self.url_open("/shop/cart", allow_redirects=False)
        self.assertEqual(page.status_code, 303)
        self.assertIn("/my2/gift-package", page.headers["Location"])

    def test_visitor_pays_after_the_email_step_only(self):
        """A payment is created for the donor of the visitor's own session:
        not before the email step, nor from another session holding the
        cart's access token."""
        self._add_fund()
        cart = self._cart()
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(cart),
            "Please give your email before paying.",
        )
        self._give_email()
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            self._assert_refused(
                f"/shop/payment/transaction/{cart.id}",
                self._payment_values(cart),
                "Please give your email before paying.",
            )
        finally:
            self.opener = own_opener
        self.assertFalse(cart.transaction_ids)
        self.make_jsonrpc_request(
            f"/shop/payment/transaction/{cart.id}", self._payment_values(cart)
        )
        self.assertEqual(len(cart.transaction_ids), 1)

    def test_an_archived_fund_is_refused(self):
        self.fund.active = False
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

    def test_email_step_never_rewrites_an_account(self):
        """A donor that became someone's account (signup links an account to
        the partner of its email) is never changed from the visitor's
        session: a new email makes a new donor."""
        self._add_fund()
        self._give_email(email="victim@example.org")
        donor = self._cart().partner_id
        self.env["res.users"].create(
            {
                "login": "victim@example.org",
                "partner_id": donor.id,
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self._give_email(email="attacker@example.org", change=True)
        self.assertEqual(donor.email, "victim@example.org")
        new_donor = self._cart().partner_id
        self.assertNotEqual(new_donor, donor)
        self.assertEqual(new_donor.email, "attacker@example.org")
        self.assertTrue(new_donor.my2_name_placeholder)

    def _saved_card(self, partner):
        provider = self.env["payment.provider"].create(
            {
                "name": "Visitor Card Provider",
                "code": "none",
                "state": "test",
                "is_published": True,
                "allow_tokenization": True,
                "company_id": self.website.company_id.id,
            }
        )
        return self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
                "partner_id": partner.id,
                "payment_details": "9876",
                "provider_ref": "saved-card",
            }
        )

    def test_standard_checkout_sends_back_to_the_gift_package(self):
        """website_sale's checkout would show a MyCompassion cart its address
        form (which edits the cart's partner) and its own payment page."""
        self._add_fund()
        self._give_email()
        for route in (
            "/shop/checkout",
            "/shop/address",
            "/shop/confirm_order",
            "/shop/payment",
        ):
            response = self.url_open(route, allow_redirects=False)
            self.assertEqual(response.status_code, 303, route)
            self.assertIn("/my2/gift-package", response.headers["Location"], route)

    def test_address_form_never_changes_the_donor(self):
        """The donor of a visitor's cart may become someone's account (signup
        links an account to the partner of its email): website_sale's address
        form must not change its email from the visitor's session."""
        self._add_fund()
        self._give_email(email="victim@example.org")
        donor = self._cart().partner_id
        page = self.url_open("/my2/gift-package?change_donor=1")
        response = self.url_open(
            "/shop/address/submit",
            data={
                "csrf_token": CSRF_RE.search(page.text).group(1),
                "partner_id": donor.id,
                "address_type": "billing",
                "name": "Eve Mallory",
                "email": "attacker@example.org",
                "phone": "+41 21 000 00 00",
                "street": "Rue du Test 1",
                "city": "Lausanne",
                "zip": "1000",
                "country_id": self.env.ref("base.ch").id,
            },
        )
        self.assertEqual(donor.email, "victim@example.org")
        self.assertTrue(donor.my2_name_placeholder)
        self.assertEqual(self._cart().partner_id, donor)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my2/gift-package", response.json()["redirectUrl"])

    def test_signup_never_takes_a_visitor_donor(self):
        """Signup moves a new account onto an existing partner of the same
        email, but never onto a visitor's donor: anyone may have typed it."""
        self._add_fund()
        self._give_email(email="victim@example.org")
        donor = self._cart().partner_id
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Victim",
                    "login": "victim@example.org",
                    "email": "victim@example.org",
                    "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )
        own_partner = user.partner_id
        self.env["res.users"]._find_and_replace_partner_async(
            user.id, "victim@example.org"
        )
        self.assertEqual(user.partner_id, own_partner)
        self.assertFalse(donor.user_ids)

    def test_signup_never_takes_a_named_visitor_donor(self):
        """Giving a name on the thank-you page needs no payment, and does not
        verify the email either: the donor is still never relinked."""
        self._add_fund()
        self._give_email(email="victim@example.org")
        donor = self._cart().partner_id
        self.assertTrue(donor.my2_email_unverified)
        self._pay("pending")
        page = self.url_open("/my2/gifts/thankyou")
        self.url_open(
            "/my2/gifts/thankyou/details",
            data={
                "csrf_token": CSRF_RE.search(page.text).group(1),
                "firstname": "Eve",
                "lastname": "Mallory",
            },
        )
        self.assertFalse(donor.my2_name_placeholder)
        self.assertTrue(donor.my2_email_unverified)
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Victim",
                    "login": "victim@example.org",
                    "email": "victim@example.org",
                    "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )
        own_partner = user.partner_id
        self.env["res.users"]._find_and_replace_partner_async(
            user.id, "victim@example.org"
        )
        self.assertEqual(user.partner_id, own_partner)
        self.assertFalse(donor.user_ids)

    def _card_saving_provider(self):
        """A published test provider that saves cards, with a payment method
        that may be saved."""
        method = self.env.ref("payment.payment_method_unknown")
        provider = self.env["payment.provider"].create(
            {
                "name": "Card Saving Provider",
                "code": "none",
                "state": "test",
                "is_published": True,
                "allow_tokenization": True,
                "company_id": self.website.company_id.id,
                "payment_method_ids": [(6, 0, method.ids)],
            }
        )
        method.active = True
        return provider

    def test_a_visitor_card_is_never_saved(self):
        """The order's partner was created from an email anyone may type, and
        may later be someone's account: a visitor is not offered to save the
        card, and a request to save it is ignored. A logged-in donor keeps
        the option."""
        provider = self._card_saving_provider()
        self._add_fund()
        self._give_email()
        cart = self._cart()
        page = self.url_open("/my2/gift-package")
        self.assertIn("o_payment_form", page.text)
        self.assertNotIn('name="o_payment_tokenize_checkbox"', page.text)
        self.make_jsonrpc_request(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(
                cart, provider_id=provider.id, tokenization_requested=True
            ),
        )
        self.assertEqual(len(cart.transaction_ids), 1)
        self.assertFalse(cart.transaction_ids.tokenize)
        self._portal_user("card-saver@example.org")
        self._add_fund()
        page = self.url_open("/my2/gift-package")
        self.assertIn('name="o_payment_tokenize_checkbox"', page.text)

    def test_visitor_never_sees_or_uses_saved_cards(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        token = self._saved_card(cart.partner_id)
        page = self.url_open("/my2/gift-package")
        self.assertNotIn("9876", page.text)
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            {
                "access_token": cart._portal_ensure_token(),
                "token_id": token.id,
                "provider_id": token.provider_id.id,
                "payment_method_id": token.payment_method_id.id,
                "amount": cart.amount_total,
                "flow": "token",
                "tokenization_requested": False,
                "landing_route": "/shop/payment/validate",
                "is_validation": False,
            },
            "Please enter your card details.",
        )
        self.assertFalse(cart.transaction_ids)

    def _payment_values(self, cart, **values):
        """What the payment form posts to create a transaction."""
        provider = self.env["payment.provider"].create(
            {
                "name": "Visitor Form Provider",
                "code": "none",
                "company_id": self.website.company_id.id,
            }
        )
        return {
            "access_token": cart._portal_ensure_token(),
            "provider_id": provider.id,
            "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
            "token_id": None,
            "amount": cart.amount_total,
            "flow": "direct",
            "tokenization_requested": False,
            "landing_route": "/shop/payment/validate",
            "is_validation": False,
            **values,
        }

    def _assert_refused(self, route, params, message, **kwargs):
        """route refuses the request with message (a UserError or a
        ValidationError, which the HTTP layer logs)."""
        with (
            self.assertLogs("odoo.http", level="WARNING") as logs,
            self.assertRaises(JsonRpcException),
        ):
            self.make_jsonrpc_request(route, params, **kwargs)
        self.assertIn(message, "\n".join(logs.output))

    def _portal_user(self, login):
        """A MyCompassion account, logged in; its password is its login."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login.split("@")[0],
                    "login": login,
                    "email": login,
                    "password": login,
                    "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )
        self.authenticate(login, login)
        return user

    def test_gift_package_pays_through_the_shop_routes(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        self.make_jsonrpc_request(
            f"/shop/payment/transaction/{cart.id}", self._payment_values(cart)
        )
        tx = cart.transaction_ids
        self.assertEqual(len(tx), 1)
        self.assertEqual(tx.amount, cart.amount_total)
        tx._set_pending()
        page = self.url_open("/shop/payment/validate")
        self.assertIn("/my2/gifts/thankyou", page.url)
        self.assertIn('action="/my2/gifts/thankyou/details"', page.text)

    def test_logged_in_donor_pays_from_the_gift_package(self):
        """The visitor's guards leave the logged-in gift flow as it was."""
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Logged Donor",
                    "login": "logged-donor@example.org",
                    "email": "logged-donor@example.org",
                    "password": "logged-donor-password",
                    "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )
        self.authenticate(user.login, "logged-donor-password")
        self._add_fund()
        cart = self._cart()
        self.assertEqual(cart.partner_id, user.partner_id)
        page = self.url_open("/my2/gift-package")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn('action="/my2/gift-package/donor"', page.text)
        self.make_jsonrpc_request(
            f"/shop/payment/transaction/{cart.id}", self._payment_values(cart)
        )
        tx = cart.transaction_ids
        self.assertEqual(len(tx), 1)
        self.assertEqual(tx.partner_id, user.partner_id)
        tx._set_pending()
        page = self.url_open("/shop/payment/validate")
        self.assertIn("/my2/gifts/thankyou", page.url)
        self.assertNotIn("Your payment did not go through", page.text)
        # As for a visitor, no second payment while this one may succeed.
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(cart),
            ALREADY_PAID,
        )
        self.assertEqual(len(cart.transaction_ids), 1)

    def test_a_user_never_pays_with_another_partners_card(self):
        """A logged-in user holding the access token of someone else's
        MyCompassion order may not pay it with that person's saved card."""
        self._add_fund()
        self._give_email()
        cart = self._cart()
        token = self._saved_card(cart.partner_id)
        self._portal_user("someone-else@example.org")
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(
                cart, flow="token", token_id=token.id, provider_id=token.provider_id.id
            ),
            "Please enter your card details.",
        )
        self.assertFalse(cart.transaction_ids)

    def test_portal_order_payment_is_refused_to_a_visitor(self):
        """sale's own payment route takes any amount and a saved card of the
        order's partner, and the gift package never uses it."""
        self._add_fund()
        self._give_email()
        cart = self._cart()
        token = self._saved_card(cart.partner_id)
        for values in (
            {"amount": 0.01},
            {
                "flow": "token",
                "token_id": token.id,
                "provider_id": token.provider_id.id,
            },
        ):
            self._assert_refused(
                f"/my/orders/{cart.id}/transaction",
                self._payment_values(cart, **values),
                "Please pay your donation from your gift package.",
            )
        self.assertFalse(cart.transaction_ids)

    def test_payment_checks_follow_the_order_not_the_host(self):
        """The cart's access token works on any host, and the shop route of
        another website of the domain resolves to that website."""
        self._add_fund()
        self._give_email()
        cart = self._cart()
        token = self._saved_card(cart.partner_id)
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        # requests files cookies under the Host header: the session goes along
        # explicitly.
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(
                cart, flow="token", token_id=token.id, provider_id=token.provider_id.id
            ),
            "Please enter your card details.",
            headers={"Host": "other.example.org", "Cookie": cookies},
        )
        self.assertFalse(cart.transaction_ids)

    def test_cart_quantity_never_reprices_a_donation(self):
        """A new quantity from website_sale's cart would price the line at the
        product's list price again (below the minimum for some funds)."""
        self._add_fund(suggested_amount="custom", custom_amount="42")
        line = self._cart().order_line
        self._assert_refused(
            "/shop/cart/update_json",
            {"product_id": line.product_id.id, "line_id": line.id, "set_qty": 2},
            "Please add and change your donations in your gift package.",
        )
        self.assertEqual((line.product_uom_qty, line.price_unit), (1.0, 42.0))

    def test_email_step_needs_a_human(self):
        self._add_fund()
        ir_http = type(self.env["ir.http"])
        with patch.object(
            ir_http, "_verify_request_recaptcha_token", return_value=False
        ):
            response = self._give_email()
        self.assertIn("donor_error=verify", response.url)
        self.assertEqual(self._cart().partner_id, self.website.partner_id)

    def test_email_step_limits_donors_per_session(self):
        self._add_fund()
        self.url_open("/my2/gift-package")
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session["my2_donors_created"] = [time.time()] * 5
        http.root.session_store.save(session)
        response = self._give_email()
        self.assertIn("donor_error=verify", response.url)
        self.assertIn("We could not verify your request", response.text)
        self.assertEqual(self._cart().partner_id, self.website.partner_id)

    def test_payment_attempts_are_limited(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        for i in range(5):
            self._pay("cancel", reference=f"my2-attempt-{i}")
        with (
            self.assertLogs("odoo.http", level="WARNING") as logs,
            self.assertRaises(JsonRpcException),
        ):
            self.make_jsonrpc_request(
                f"/shop/payment/transaction/{cart.id}",
                {"access_token": cart._portal_ensure_token()},
            )
        self.assertIn("Too many payment attempts", "\n".join(logs.output))
        self.assertEqual(len(cart.transaction_ids), 5)

    def test_email_step_needs_consent_and_a_valid_email(self):
        self._add_fund()
        for email, consent in (("not-an-email", "on"), ("donor@example.org", None)):
            response = self._give_email(email=email, consent=consent)
            self.assertIn('action="/my2/gift-package/donor"', response.text)
            self.assertEqual(self._cart().partner_id, self.website.partner_id)

    # === Payment attempts per client IP ===

    def _visitor_pays(self, **headers):
        """A new visitor - a browser of their own, with its session, cart and
        donor - starts a payment. Whether it was accepted."""
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            self._add_fund()
            self._give_email()
            cart = self._cart()
            try:
                self.make_jsonrpc_request(
                    f"/shop/payment/transaction/{cart.id}",
                    self._payment_values(cart),
                    headers=headers,
                )
            except JsonRpcException:
                return False
            return bool(cart.transaction_ids)
        finally:
            self.opener = own_opener

    def test_payment_attempts_are_limited_per_ip(self):
        """Card testers start a new session and cart for each card: the
        attempts of a client IP are counted on the website, all carts and
        sessions together."""
        self.assertFalse(
            self.env["ir.config_parameter"].get_param("recaptcha_private_key"),
            "the reCAPTCHA of the email step lets everyone through",
        )
        self.website.my2_max_payment_attempts_per_ip = 3
        self.assertEqual(
            [self._visitor_pays() for _attempt in range(4)], [True, True, True, False]
        )
        # Behind the proxy (proxy_mode), the client's own address counts.
        with patch.dict(config.options, {"proxy_mode": True}):
            self.assertTrue(
                self._visitor_pays(
                    **{
                        "X-Forwarded-For": "203.0.113.7",
                        "X-Forwarded-Host": urlparse(self.base_url()).netloc,
                    }
                )
            )

    def test_payment_attempts_per_ip_with_recaptcha_keys(self):
        """The limit is the same once the reCAPTCHA of the email step has
        its keys."""
        ICP = self.env["ir.config_parameter"]
        ICP.set_param("recaptcha_public_key", "test-public-key")
        ICP.set_param("recaptcha_private_key", "test-private-key")
        self.website.my2_max_payment_attempts_per_ip = 1
        with patch.object(
            type(self.env["ir.http"]),
            "_verify_recaptcha_token",
            return_value="is_human",
        ) as verify:
            self.assertEqual(
                [self._visitor_pays() for _attempt in range(2)], [True, False]
            )
        self.assertTrue(verify.called)

    def test_payment_attempts_per_ip_start_again_after_the_window(self):
        self.website.my2_max_payment_attempts_per_ip = 1
        self.assertEqual([self._visitor_pays() for _attempt in range(2)], [True, False])
        counter = self.env["my2.payment.attempt.counter"].search(
            [("website_id", "=", self.website.id)]
        )
        self.assertEqual(counter.attempts, 1)
        counter.window_start -= timedelta(
            minutes=self.website.my2_payment_attempts_window + 1
        )
        self.assertTrue(self._visitor_pays())
        self.assertEqual(counter.attempts, 1)

    def test_expired_attempt_counters_are_removed(self):
        self.assertTrue(self._visitor_pays())
        counter = self.env["my2.payment.attempt.counter"].search(
            [("website_id", "=", self.website.id)]
        )
        counter._gc_my2_expired_counters()
        self.assertTrue(counter.exists())
        counter.window_start -= timedelta(
            minutes=self.website.my2_payment_attempts_window + 1
        )
        counter._gc_my2_expired_counters()
        self.assertFalse(counter.exists())

    # === The name, after the payment ===

    def test_thank_you_page_asks_the_name_once(self):
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        self._pay("pending")
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
        """The name form only ever names the donor of its own session: another
        visitor, with a valid form of their own, names their donor only."""
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        self._pay("pending", reference="my2-first-session")
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            self._add_fund()
            self._give_email(email="eve@example.org")
            other_donor = self._cart().partner_id
            self.assertNotEqual(other_donor, donor)
            self._pay("pending", reference="my2-other-session")
            page = self.url_open("/my2/gifts/thankyou")
            response = self.url_open(
                "/my2/gifts/thankyou/details",
                data={
                    "csrf_token": CSRF_RE.search(page.text).group(1),
                    "firstname": "Eve",
                    "lastname": "Mallory",
                },
                allow_redirects=False,
            )
        finally:
            self.opener = own_opener
        # The request reached the route (a missing CSRF token is a 400).
        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            (other_donor.firstname, other_donor.lastname), ("Eve", "Mallory")
        )
        self.assertTrue(donor.my2_name_placeholder)

    # === A failed payment is no thank-you ===

    def _pay(self, state, reference=None, **values):
        cart = self._cart()
        provider = self.env["payment.provider"].create(
            {
                "name": "Visitor Test Provider",
                "code": "none",
                "company_id": self.website.company_id.id,
            }
        )
        return self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
                "amount": cart.amount_total,
                "currency_id": cart.currency_id.id,
                "partner_id": cart.partner_id.id,
                "reference": reference or f"my2-visitor-{state}",
                "sale_order_ids": [(6, 0, cart.ids)],
                "state": state,
                **values,
            }
        )

    def test_failed_payment_goes_back_to_the_basket(self):
        self._add_fund()
        self._give_email()
        self._pay("cancel")
        # A payment pending first (late 3-D Secure, BLIK) made it a sent
        # quotation: still unpaid.
        self._cart().state = "sent"
        # The landing route of the payment form, as after a refused card: it
        # empties the cart (sale_reset), then confirmation -> thank-you.
        page = self.url_open("/shop/payment/validate")
        self.assertIn("/my2/gift-package", page.url)
        self.assertIn("payment_failed=1", page.url)
        self.assertIn("Your payment did not go through", page.text)
        self.assertNotIn('action="/my2/gifts/thankyou/details"', page.text)
        # The cart is back, with its donor: the donation can be paid again
        # (the payment form itself depends on the providers of the database).
        self.assertIn("Visitor Test Fund", page.text)
        self.assertNotIn('action="/my2/gift-package/donor"', page.text)
        self.assertEqual(self._cart().state, "draft")

    def test_named_donor_keeps_the_cart_after_a_failed_payment(self):
        # The name may be typed on the thank-you page while the payment is
        # still pending; when it is refused afterwards, the cart goes back to
        # the same donor, without asking the email again.
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        tx = self._pay("pending")
        page = self.url_open("/my2/gifts/thankyou")
        self.url_open(
            "/my2/gifts/thankyou/details",
            data={
                "csrf_token": CSRF_RE.search(page.text).group(1),
                "firstname": "Anna",
                "lastname": "Nowak",
            },
        )
        self.assertFalse(donor.my2_name_placeholder)
        partners = self.env["res.partner"].search_count([])
        tx._set_canceled()
        page = self.url_open("/shop/payment/validate")
        self.assertIn("payment_failed=1", page.url)
        self.assertNotIn('action="/my2/gift-package/donor"', page.text)
        self.assertIn("donor@example.org", page.text)
        self.assertEqual(self._cart().partner_id, donor)
        self.assertEqual(self.env["res.partner"].search_count([]), partners)
        self.assertEqual((donor.firstname, donor.lastname), ("Anna", "Nowak"))

    def _monitor(self, tx):
        """What /shop/payment/transaction does: the status page follows tx."""
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session[PaymentPostProcessing.MONITORED_TX_ID_KEY] = tx.id
        http.root.session_store.save(session)

    def _land_on_another_host(self):
        """Follow the payment form's landing route on the host of another
        website of the domain (/my2 is served on any domain, /shop routes
        resolve to the website of the host): the page the donor ends on."""
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_website.domain = "http://other.example.org"
        # requests files cookies under the Host header: the session goes along
        # explicitly.
        cookies = "; ".join(f"{c.name}={c.value}" for c in self.opener.cookies)
        headers = {"Host": "other.example.org", "Cookie": cookies}
        validate = self.url_open(
            "/shop/payment/validate", headers=headers, allow_redirects=False
        )
        self.assertEqual(validate.status_code, 303)
        self.assertEqual(
            urlparse(validate.headers["Location"]).path, "/shop/confirmation"
        )
        confirmation = self.url_open(
            "/shop/confirmation", headers=headers, allow_redirects=False
        )
        self.assertEqual(confirmation.status_code, 303)
        self.assertEqual(
            urlparse(confirmation.headers["Location"]).path, "/my2/gifts/thankyou"
        )
        return self.url_open("/my2/gifts/thankyou")

    def test_pending_payment_lands_on_the_thank_you_page_from_another_host(self):
        self._add_fund()
        self._give_email()
        self._pay("pending")
        page = self._land_on_another_host()
        self.assertIn('action="/my2/gifts/thankyou/details"', page.text)

    def test_refused_payment_lands_on_the_basket_from_another_host(self):
        self._add_fund()
        self._give_email()
        self._pay("cancel")
        page = self._land_on_another_host()
        self.assertIn("payment_failed=1", page.url)
        self.assertIn("Visitor Test Fund", page.text)

    def test_paid_donation_lands_on_the_thank_you_page_from_another_host(self):
        self._add_fund()
        self._give_email()
        self._pay("done")
        page = self._land_on_another_host()
        self.assertIn("/my2/gifts/thankyou", page.url)
        self.assertNotIn("Your payment did not go through", page.text)

    def test_logged_in_donor_with_another_cart_lands_on_the_thank_you_page(self):
        """The website of the host has a cart of its own for the donor: the
        landing route still validates the donation."""
        user = self._portal_user("donor-with-a-shop-cart@example.org")
        self._add_fund()
        cart = self._cart()
        self.url_open("/my2/gift-package")
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        shop_cart = self.env["sale.order"].create(
            {
                "partner_id": user.partner_id.id,
                "website_id": other_website.id,
                "company_id": other_website.company_id.id,
                "order_line": [(0, 0, {"product_id": self._shop_product().id})],
            }
        )
        self._pay("pending")
        page = self._land_on_another_host()
        self.assertIn("/my2/gifts/thankyou", page.url)
        self.assertNotIn("/my2/gift-package", page.url)
        self.assertEqual(cart.transaction_ids.state, "pending")
        self.assertEqual(shop_cart.state, "draft")

    def test_status_page_of_a_pending_payment(self):
        """A visitor's status page keeps polling while the payment is pending
        (BLIK, 3DS): the post-processing must not leave the request anything
        the public user may not save."""
        self._add_fund()
        self._give_email()
        tx = self._pay("pending")
        self._monitor(tx)
        result = self.make_jsonrpc_request("/payment/status/poll", {})
        self.assertEqual(result["state"], "pending")
        self.assertEqual(self._cart().state, "sent")

    def test_pending_post_processing_leaves_nothing_to_save(self):
        """The poll post-processes in sudo, but its request saves what is left
        as the visitor, who may not read order lines (AccessError, and a
        status page that stops polling). Post-processing a pending payment
        turns the quotation into a sent one, whose line amounts must be saved
        before the request ends."""
        self._add_fund()
        self._give_email()
        tx = self._pay("pending")
        self.env.flush_all()
        tx._post_process()
        self.assertEqual(self._cart().state, "sent")
        self.assertFalse(self.env.transaction.tocompute)
        self.assertFalse(list(self.env.cache.get_dirty_fields()))

    def _assert_thanked_despite_a_later_cancel(self, **earlier):
        self._add_fund()
        self._give_email()
        self._pay(reference="my2-earlier", **earlier)
        self._pay("cancel", reference="my2-later")
        page = self.url_open("/shop/payment/validate")
        self.assertNotIn("/my2/gift-package", page.url)
        self.assertNotIn("Your payment did not go through", page.text)

    def test_no_second_payment_while_one_is_pending(self):
        """A payment still pending (BLIK waiting in the bank app, another tab)
        thanks the donor even when a later attempt was cancelled: offering the
        cart again could charge them twice."""
        self._assert_thanked_despite_a_later_cancel(state="pending")

    def test_no_second_payment_while_the_provider_has_one(self):
        self._assert_thanked_despite_a_later_cancel(
            state="draft", provider_reference="AT-THE-PROVIDER"
        )

    def test_second_tab_cannot_pay_while_one_is_pending(self):
        """The basket open in two tabs: tab A's payment is pending (BLIK in
        the bank app, 3-D Secure) when tab B pays."""
        self._add_fund()
        self._give_email()
        cart = self._cart()
        self._pay("pending")
        self._assert_refused(
            f"/shop/payment/transaction/{cart.id}",
            self._payment_values(cart),
            ALREADY_PAID,
        )
        self.assertEqual(len(cart.transaction_ids), 1)

    def test_one_card_per_order_when_the_card_is_sent(self):
        """Two payment forms of one order each made a draft before either
        card was sent: once one payment is under way, the other card is
        refused."""
        self._add_fund()
        self._give_email()
        first = self._pay("draft", reference="my2-first-form")
        second = self._pay("draft", reference="my2-second-form")
        first._my2_check_card_submission()
        second._my2_check_card_submission()
        first._set_pending()
        first._my2_check_card_submission()  # its own payment does not count
        with self.assertRaisesRegex(
            UserError,
            re.escape(ALREADY_PAID),
        ):
            second._my2_check_card_submission()
        # Only MyCompassion orders: another website's order is left alone.
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_order = self.env["sale.order"].create(
            {
                "partner_id": other_website.partner_id.id,
                "website_id": other_website.id,
                "company_id": other_website.company_id.id,
            }
        )
        other_tx = first.copy(
            {"reference": "my2-other-website", "sale_order_ids": other_order.ids}
        )
        other_tx.copy(
            {
                "reference": "my2-other-website-pending",
                "sale_order_ids": other_order.ids,
            }
        )._set_pending()
        other_tx._my2_check_card_submission()

    def test_an_unconfirmed_refusal_is_no_failure(self):
        """A payment the provider never confirmed nor refused, given up on
        after a while, may still succeed: the donor is not asked to pay
        again."""
        self._add_fund()
        self._give_email()
        cart = self._cart()
        self._pay("error")
        with patch.object(
            type(self.env["payment.transaction"]),
            "_my2_refusal_is_certain",
            return_value=False,
        ):
            page = self.url_open("/shop/payment/validate")
            self.assertNotIn("/my2/gift-package", page.url)
            self.assertNotIn("Your payment did not go through", page.text)
            self._assert_refused(
                f"/shop/payment/transaction/{cart.id}",
                self._payment_values(cart),
                ALREADY_PAID,
            )
        self.assertEqual(len(cart.transaction_ids), 1)
        # A refusal the provider is sure of gives the basket back.
        page = self.url_open("/my2/gifts/thankyou")
        self.assertIn("payment_failed=1", page.url)

    def test_abandoned_draft_hides_no_refusal(self):
        self._add_fund()
        self._give_email()
        self._pay("cancel")
        self._pay("draft")
        page = self.url_open("/shop/payment/validate")
        self.assertIn("payment_failed=1", page.url)

    def test_no_thanks_without_a_payment(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session["sale_last_order_id"] = cart.id
        http.root.session_store.save(session)
        page = self.url_open("/my2/gifts/thankyou")
        self.assertIn("/my2/gift-package", page.url)
        self.assertNotIn("payment_failed=1", page.url)
        self.assertNotIn('action="/my2/gifts/thankyou/details"', page.text)

    def test_thank_you_page_reads_an_order_of_its_website(self):
        """The session's last order may come from another website of the
        domain (crowdfunding, events): it is neither thanked nor restored."""
        other_website = self.env["website"].search(
            [("id", "!=", self.website.id), ("is_my_compassion", "=", False)], limit=1
        )
        other_order = self.env["sale.order"].create(
            {
                "partner_id": other_website.partner_id.id,
                "website_id": other_website.id,
                "company_id": other_website.company_id.id,
                "state": "sent",
            }
        )
        # A session the server keeps (a page alone does not store it).
        self._add_fund()
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session["sale_last_order_id"] = other_order.id
        http.root.session_store.save(session)
        page = self.url_open("/my2/gifts/thankyou", allow_redirects=False)
        self.assertEqual(other_order.state, "sent")
        self.assertEqual(page.status_code, 303)
        self.assertTrue(page.headers["Location"].endswith("/my2/gifts"))

    def test_thank_you_after_a_done_payment(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        self.url_open("/my2/gift-package")
        self._pay("done")
        cart.action_confirm()
        page = self.url_open("/my2/gifts/thankyou")
        self.assertNotIn("/my2/gift-package", page.url)
        self.assertNotIn("Your payment did not go through", page.text)

    # === No Odoo sales email for a donation ===

    def test_no_sales_email_for_a_my_compassion_order(self):
        self._add_fund()
        self._give_email()
        cart = self._cart().sudo()
        template = self.env.ref("sale.mail_template_sale_confirmation")
        messages = len(cart.message_ids)
        cart._send_order_notification_mail(template)
        self.assertEqual(len(cart.message_ids), messages)

    # === Duplicates and abandoned donors ===

    def test_second_donation_of_the_session_keeps_its_donor(self):
        self._add_fund()
        self._give_email()
        first_cart = self._cart()
        donor = first_cart.partner_id
        self._pay("done")
        first_cart.action_confirm()
        self.url_open("/shop/payment/validate")
        partners = self.env["res.partner"].search_count([])
        self._add_fund()
        second_cart = self._cart()
        self.assertNotEqual(second_cart, first_cart)
        self._give_email()
        self.assertEqual(second_cart.partner_id, donor)
        self.assertEqual(self.env["res.partner"].search_count([]), partners)

    def test_replayed_email_step_keeps_the_donor(self):
        """A double click: the replayed request has not seen the session of
        the first one, but finds its donor on the cart."""
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        session = http.root.session_store.get(self.opener.cookies["session_id"])
        session.pop("my2_donor_partner_id")
        http.root.session_store.save(session)
        partners = self.env["res.partner"].search_count([])
        self._give_email()
        self.assertEqual(self._cart().partner_id, donor)
        self.assertEqual(self.env["res.partner"].search_count([]), partners)

    def _abandoned_and_paid_donors(self):
        self._add_fund()
        self._give_email()
        abandoned = self._cart().partner_id
        paid = self.env["res.partner"].create(
            {
                "lastname": abandoned.MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": "p@example.org",
            }
        )
        self._pay("done").partner_id = paid
        old = fields.Datetime.now() - timedelta(days=40)
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id IN %s",
            [old, tuple((abandoned | paid).ids)],
        )
        (abandoned | paid).invalidate_recordset(["create_date"])
        return abandoned, paid

    def test_abandoned_donors_are_archived(self):
        abandoned, paid = self._abandoned_and_paid_donors()
        self.env["res.partner"]._my2_cron_archive_abandoned_donors()
        self.assertFalse(abandoned.active)
        self.assertTrue(paid.active)

    def test_donors_kept_never_stall_the_cleanup(self):
        """The donors the cleanup keeps (paid, with an account...) stay
        placeholders: they must not fill every batch of later runs, whichever
        end of the list a batch is read from."""
        older = self.env["res.partner"].create(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": "older@example.org",
            }
        )
        abandoned, newer = self._abandoned_and_paid_donors()
        self._pay("done", reference="my2-older-paid").partner_id = older
        self.env.cr.execute(
            "UPDATE res_partner SET create_date = %s WHERE id = %s",
            [fields.Datetime.now() - timedelta(days=40), older.id],
        )
        older.invalidate_recordset(["create_date"])
        self.assertLess(older.id, abandoned.id)
        self.assertLess(abandoned.id, newer.id)
        self.env["res.partner"]._my2_cron_archive_abandoned_donors(limit=1)
        self.assertFalse(abandoned.active)
        self.assertTrue(older.active)
        self.assertTrue(newer.active)

    def test_donor_of_an_uncertain_payment_is_kept(self):
        """A refused payment whose refusal is not certain may still succeed."""
        abandoned, _paid = self._abandoned_and_paid_donors()
        self._pay("error")
        with patch.object(
            type(self.env["payment.transaction"]),
            "_my2_refusal_is_certain",
            return_value=False,
        ):
            self.env["res.partner"]._my2_cron_archive_abandoned_donors()
        self.assertTrue(abandoned.active)

    def test_donor_of_a_payment_at_the_provider_is_kept(self):
        abandoned, _paid = self._abandoned_and_paid_donors()
        self._pay("draft", provider_reference="AT-THE-PROVIDER")
        self.env["res.partner"]._my2_cron_archive_abandoned_donors()
        self.assertTrue(abandoned.active)

    # === What waits for the donor's name ===

    def _letter_config(self, model="account.move"):
        """A communication about invoices (as the thank-you letters and the
        donation receipts), or about another model, that greets the donor by
        name."""
        template = self.env["mail.template"].create(
            {
                "name": "Visitor Thanks",
                "model_id": self.env["ir.model"]._get_id("partner.communication.job"),
                "subject": "Thank you",
                "email_from": "thanks@example.org",
                "body_html": '<p>Dear <t t-out="object.partner_id.name"/></p>',
            }
        )
        return self.env["partner.communication.config"].create(
            {
                "name": "Visitor Thanks",
                "model_id": self.env["ir.model"]._get_id(model),
                "source_id": self.env["utm.source"].create({"name": "Thanks"}).id,
                "send_mode": "digital",
                "email_template_id": template.id,
                "forbid_merging": True,
            }
        )

    def _letter(self, config, donor, **values):
        invoice = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": donor.id}
        )
        return self.env["partner.communication.job"].create(
            {
                "config_id": config.id,
                "partner_id": donor.id,
                "object_ids": str(invoice.id),
                "send_mode": "digital",
                **values,
            }
        )

    def test_thank_you_letter_waits_for_the_name(self):
        config = self._letter_config()
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        job = self._letter(config, donor, auto_send=True)
        self.assertIn(donor.MY2_PLACEHOLDER_NAME, job.body_html)
        # Sent alone (the queued automatic send, or a click on Send): nothing
        # fails, and the user is told why.
        action = job.send()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(job.state, "pending")
        # Sent in a batch: left pending, until the name comes.
        other_donor = donor.copy(
            {"my2_name_placeholder": True, "email": "other@example.org"}
        )
        jobs = job | self._letter(config, other_donor)
        jobs.send()
        self.assertEqual(set(jobs.mapped("state")), {"pending"})

    def test_held_letters_go_once_the_name_is_given(self):
        """The text is rendered again with the real name; what was to be sent
        automatically is sent, the rest waits for staff."""
        config = self._letter_config()
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id.with_context(queue_job__no_delay=True)
        automatic = self._letter(config, donor, auto_send=True)
        manual = self._letter(config, donor)
        for job in automatic | manual:
            self.assertIn(donor.MY2_PLACEHOLDER_NAME, job.body_html)
        donor._my2_replace_placeholder_name("Anna", "Nowak")
        for job in automatic | manual:
            self.assertIn("Nowak", job.body_html)
            self.assertNotIn(donor.MY2_PLACEHOLDER_NAME, job.body_html)
        self.assertEqual(automatic.state, "done")
        self.assertEqual(manual.state, "pending")

    def _queued_sends(self, letter):
        """The queued sends of letter."""
        if "queue.job" in self.env:
            jobs = self.env["queue.job"].search(
                [
                    ("model_name", "=", letter._name),
                    ("method_name", "=", "send"),
                    ("record_ids", "like", str(letter.id)),
                ]
            )
        else:
            jobs = self.env["queue.job.replacement"].search(
                [
                    ("res_model", "=", letter._name),
                    ("job_function", "=", "send"),
                    ("res_ids", "=", str(letter.ids)),
                ]
            )
        return jobs

    def test_held_letter_released_by_the_visitor_is_sent_as_superuser(self):
        """The name form of the thank-you page runs as the public user: the
        release it triggers renders and queues the letter as the superuser,
        not as the visitor."""
        config = self._letter_config()
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        letter = self._letter(config, donor, auto_send=True)
        self.assertIn(donor.MY2_PLACEHOLDER_NAME, letter.body_html)
        queued_before = self._queued_sends(letter)
        self._pay("pending")
        page = self.url_open("/my2/gifts/thankyou")
        self.url_open(
            "/my2/gifts/thankyou/details",
            data={
                "csrf_token": CSRF_RE.search(page.text).group(1),
                "firstname": "Anna",
                "lastname": "Nowak",
            },
        )
        self.assertIn("Nowak", letter.body_html)
        released = self._queued_sends(letter) - queued_before
        self.assertEqual(len(released), 1)
        self.assertEqual(released.user_id, self.env.ref("base.user_root"))

    def test_portal_invitation_released_by_the_visitor_comes_from_superuser(self):
        """A donor who also signed up for a sponsorship gets the portal
        invitation once named: given through the thank-you form, which runs
        as the public user, it is still created as the superuser."""
        config = self._letter_config(model="res.partner")
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        group = self.env["recurring.contract.group"].create({"partner_id": donor.id})
        self.env["recurring.contract"].create(
            {"partner_id": donor.id, "group_id": group.id, "my2_signup": True}
        ).state = "waiting"
        self._pay("pending")
        page = self.url_open("/my2/gifts/thankyou")
        with patch.object(
            type(self.env["recurring.contract"]),
            "_my2_portal_invitation_config",
            return_value=config,
        ):
            self.url_open(
                "/my2/gifts/thankyou/details",
                data={
                    "csrf_token": CSRF_RE.search(page.text).group(1),
                    "firstname": "Anna",
                    "lastname": "Nowak",
                },
            )
        invitation = self.env["partner.communication.job"].search(
            [("config_id", "=", config.id), ("partner_id", "=", donor.id)]
        )
        self.assertEqual(len(invitation), 1)
        self.assertEqual(invitation.create_uid, self.env.ref("base.user_root"))

    def test_every_held_letter_is_sent(self):
        """Two automatic letters of one rule for one donor (the rule does not
        merge them) are both sent once the name is given: the queue does not
        take the second send for a duplicate of the first."""
        config = self._letter_config()
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        letters = self._letter(config, donor, auto_send=True) | self._letter(
            config, donor, auto_send=True
        )
        job_class = type(self.env["partner.communication.job"])
        with patch.object(job_class, "with_delay_sh", autospec=True) as delay:
            donor._my2_replace_placeholder_name("Anna", "Nowak")
        sends = [c for c in delay.call_args_list if c.args[1] == "send"]
        self.assertEqual({c.args[0] for c in sends}, set(letters))
        keys = {c.kwargs["identity_key"] for c in sends}
        self.assertEqual(len(keys), 2, keys)

    def test_a_name_typed_by_staff_releases_the_letters(self):
        """Staff may call the donor and type their name on the partner."""
        config = self._letter_config()
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id.with_context(queue_job__no_delay=True)
        job = self._letter(config, donor, auto_send=True)
        self.assertIn(donor.MY2_PLACEHOLDER_NAME, job.body_html)
        donor.write({"phone": "+48 600 000 000"})
        self.assertTrue(donor.my2_name_placeholder)
        donor.write({"firstname": "Anna"})
        self.assertTrue(donor.my2_name_placeholder, "the surname is still missing")
        donor.write({"lastname": "Nowak"})
        self.assertFalse(donor.my2_name_placeholder)
        self.assertIn("Nowak", job.body_html)
        self.assertEqual(job.state, "done")

    # === Amounts and images ===

    def test_pricelist_routes_never_change_the_cart(self):
        """website_sale's pricelist routes (/shop/change_pricelist,
        /shop/pricelist) would move the cart to another pricelist: the amounts
        the donor chose would be read in its currency."""
        self._add_fund(suggested_amount="custom", custom_amount="42")
        cart = self._cart()
        pricelist = cart.pricelist_id
        currency = self.env.ref("base.EUR")
        if currency == cart.currency_id:
            currency = self.env.ref("base.USD")
        currency.active = True
        other = self.env["product.pricelist"].create(
            {"name": "Another Currency", "currency_id": currency.id}
        )
        cart._cart_update_pricelist(pricelist_id=other.id)
        self.assertEqual(cart.pricelist_id, pricelist)
        self.assertEqual(cart.order_line.price_unit, 42.0)

    def test_chosen_amounts_are_never_reset(self):
        self._add_fund(suggested_amount="custom", custom_amount="42")
        cart = self._cart()
        self.assertFalse(cart._get_update_prices_lines())
        cart._recompute_prices()
        self.assertEqual(cart.order_line.price_unit, 42.0)

    def test_visitor_sees_the_fund_image(self):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        self.fund.my_compassion_image = base64.b64encode(png)
        response = self.url_open(
            f"/web/image/product.template/{self.fund.id}/my_compassion_image"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, png)


@tagged("post_install", "-at_install")
class TestConcurrentPayments(TransactionCase):
    """Two requests paying one MyCompassion order at the same time - two
    tabs, or a script - each in its own database transaction."""

    def setUp(self):
        super().setUp()
        website = self.env.ref("my_compassion.my2_website")
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            self.order_id = (
                env["sale.order"]
                .create(
                    {
                        "partner_id": website.partner_id.id,
                        "website_id": website.id,
                        "company_id": website.company_id.id,
                    }
                )
                .id
            )
            self.provider_id = (
                env["payment.provider"]
                .create(
                    {
                        "name": "Concurrent Payments Provider",
                        "code": "none",
                        "company_id": website.company_id.id,
                    }
                )
                .id
            )
        self.addCleanup(self._remove_committed_records)
        self.first, self.second = self.registry.cursor(), self.registry.cursor()
        self.addCleanup(self.first.close)
        self.addCleanup(self.second.close)

    def _remove_committed_records(self):
        """Through the ORM, so that the order's messages and followers go too."""
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            order = env["sale.order"].browse(self.order_id)
            order.transaction_ids.unlink()
            # A pending payment made the quotation a sent one.
            order.filtered(lambda o: o.state == "sent").action_draft()
            order.unlink()
            env["payment.provider"].browse(self.provider_id).unlink()
        self._assert_nothing_left()

    def _assert_nothing_left(self):
        """The fixtures were committed: nothing of them may stay behind."""
        with self.registry.cursor() as cr:
            for query in (
                "SELECT count(*) FROM sale_order WHERE id = %(order)s",
                "SELECT count(*) FROM sale_order_transaction_rel"
                " WHERE sale_order_id = %(order)s",
                "SELECT count(*) FROM payment_provider WHERE id = %(provider)s",
                "SELECT count(*) FROM mail_message"
                " WHERE model = 'sale.order' AND res_id = %(order)s",
                "SELECT count(*) FROM mail_followers"
                " WHERE res_model = 'sale.order' AND res_id = %(order)s",
            ):
                cr.execute(
                    query, {"order": self.order_id, "provider": self.provider_id}
                )
                self.assertEqual(cr.fetchone()[0], 0, query)

    def _pay(self, cr):
        """What the payment routes do: the check, then the transaction - left
        pending, as a payment the provider may still confirm."""
        env = api.Environment(cr, SUPERUSER_ID, {})
        env["sale.order"].browse(self.order_id)._my2_lock_for_new_payment()
        return self._transaction(env, "pending")

    def _transaction(self, env, state):
        order = env["sale.order"].browse(self.order_id)
        return env["payment.transaction"].create(
            {
                "provider_id": self.provider_id,
                "payment_method_id": env.ref("payment.payment_method_unknown").id,
                "amount": 50.0,
                "currency_id": order.currency_id.id,
                "partner_id": order.partner_id.id,
                "reference": f"my2-concurrent-{uuid4().hex}",
                "sale_order_ids": [(6, 0, order.ids)],
                "state": state,
            }
        )

    def _transaction_count(self):
        with self.registry.cursor() as cr:
            cr.execute(
                "SELECT count(*) FROM sale_order_transaction_rel"
                " WHERE sale_order_id = %s",
                [self.order_id],
            )
            return cr.fetchone()[0]

    def test_a_payment_being_created_is_never_doubled(self):
        self._pay(self.first)
        with self.assertRaisesRegex(
            UserError, re.escape("Payment is already being processed.")
        ):
            self._pay(self.second)
        self.second.rollback()
        self.first.commit()
        self.assertEqual(self._transaction_count(), 1)

    def test_a_payment_committed_meanwhile_is_never_doubled(self):
        """The second request started before the first one committed: at
        REPEATABLE READ its snapshot does not hold the first payment."""
        self.second.execute("SELECT 1")
        self._pay(self.first)
        self.first.commit()
        with self.assertRaises(SerializationFailure):
            self._pay(self.second)
        # What Odoo does with a serialization failure: replay the request.
        self.second.rollback()
        with self.assertRaisesRegex(
            UserError,
            re.escape(ALREADY_PAID),
        ):
            self._pay(self.second)
        self.second.rollback()
        self.assertEqual(self._transaction_count(), 1)

    def test_a_card_sent_meanwhile_is_never_doubled(self):
        """Two payment forms of the order made a draft each; the second card
        is sent by a request whose snapshot predates the first card."""
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            first_id = self._transaction(env, "draft").id
            second_id = self._transaction(env, "draft").id
        self.second.execute("SELECT 1")
        first = api.Environment(self.first, SUPERUSER_ID, {})["payment.transaction"]
        first.browse(first_id)._my2_check_card_submission()
        first.browse(first_id)._set_pending()
        self.first.commit()
        second = api.Environment(self.second, SUPERUSER_ID, {})["payment.transaction"]
        with self.assertRaises(SerializationFailure):
            second.browse(second_id)._my2_check_card_submission()
        # What Odoo does with a serialization failure: replay the request.
        self.second.rollback()
        second = api.Environment(self.second, SUPERUSER_ID, {})["payment.transaction"]
        with self.assertRaisesRegex(
            UserError,
            re.escape(ALREADY_PAID),
        ):
            second.browse(second_id)._my2_check_card_submission()
        self.second.rollback()


@tagged("post_install", "-at_install")
class TestEmailUnverifiedPostMigration(TransactionCase):
    """The post-migration to 18.0.1.0.30 flags the partners the fast checkout
    created from a visitor's email before my2_email_unverified existed."""

    def test_placeholder_partners_without_an_account_are_flagged(self):
        Partner = self.env["res.partner"]
        placeholder = {
            "lastname": Partner.MY2_PLACEHOLDER_NAME,
            "firstname": False,
            "my2_name_placeholder": True,
        }
        waiting = Partner.create({**placeholder, "email": "waiting@example.org"})
        with_account = Partner.create({**placeholder, "email": "account@example.org"})
        self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "login": "account@example.org",
                "partner_id": with_account.id,
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        named = Partner.create({"name": "Named Sponsor", "email": "named@example.org"})
        partners = waiting | with_account | named
        self.assertFalse(any(partners.mapped("my2_email_unverified")))
        self.env.flush_all()
        migrate = load_script(
            "my_compassion/migrations/18.0.1.0.30/post-email-unverified.py",
            "my_compassion_post_email_unverified_18_0_1_0_30",
        ).migrate
        for _run in range(2):  # a second run changes nothing
            migrate(self.env.cr, "18.0.1.0.29")
            partners.invalidate_recordset(["my2_email_unverified"])
            self.assertEqual(
                partners.mapped("my2_email_unverified"), [True, False, False]
            )
