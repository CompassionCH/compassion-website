import re

from odoo import http
from odoo.tests import tagged
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    HttpCase,
    JsonRpcException,
    Opener,
)

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

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

    def test_visitor_never_sees_or_uses_saved_cards(self):
        self._add_fund()
        self._give_email()
        cart = self._cart()
        token = self._saved_card(cart.partner_id)
        page = self.url_open("/my2/gift-package")
        self.assertNotIn("9876", page.text)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
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
            )
        self.assertFalse(cart.transaction_ids)

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

    # === PayU never shows the placeholder ===

    def test_no_placeholder_name_sent_to_payu(self):
        tx_model = self.env["payment.transaction"]
        if "payu_gpo_cardholder_name" not in tx_model._fields:
            self.skipTest("payment_payu_gpo is not installed")
        self._add_fund()
        self._give_email()
        donor = self._cart().partner_id
        tx = tx_model.new({"partner_id": donor.id, "partner_name": donor.name})
        self.assertEqual(tx._payu_gpo_buyer_names(), ("", ""))
        # The name on the card, once typed, is sent.
        tx.payu_gpo_cardholder_name = "Anna Nowak"
        self.assertEqual(tx._payu_gpo_buyer_names(), ("Anna", "Nowak"))

    # === No Odoo sales email for a donation ===

    def test_no_sales_email_for_a_my_compassion_order(self):
        self._add_fund()
        self._give_email()
        cart = self._cart().sudo()
        template = self.env.ref("sale.mail_template_sale_confirmation")
        messages = len(cart.message_ids)
        cart._send_order_notification_mail(template)
        self.assertEqual(len(cart.message_ids), messages)
