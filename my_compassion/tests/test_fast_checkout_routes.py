import re
import unittest
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    HttpCase,
    JsonRpcException,
    Opener,
)

from .common import DigitalSeamCase

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
WIZARD_ID_RE = re.compile(r'name="wizard_id"\s+value="(\d+)"')
ACCESS_TOKEN_RE = re.compile(r"access_token=([0-9a-f]+)")


@tagged("post_install", "-at_install")
class TestFastCheckoutRoutes(HttpCase, DigitalSeamCase):
    """The /my2/new-sponsorship/* surface, walked over HTTP.

    The rest of the fast-checkout suite drives the wizard model and renders
    its templates inside a MockRequest. This walks the same checkout through
    the real WSGI stack instead, which is the only place the parts that
    belong to the request rather than to the model show up: the routing, the
    csrf-protected posts, the access tokens the payment routes are guarded
    by, and - the one the pay-first design newly depends on - the session
    that tells the thank-you page whether the visitor reading it is the one
    who just paid.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Host-based website resolution: the test client talks to 127.0.0.1,
        # which matches no configured domain, so the request would otherwise
        # land on whichever website happens to come first - and the checkout
        # templates only exist on the one the MyCompassion theme is applied
        # to. Rolled back with the rest of the transaction.
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        cls.web_company = cls.website.company_id

        # The mode buttons of the page, and the payment page behind one of
        # them, are scoped to the website's company: a mode published
        # anywhere else is invisible to this checkout (see
        # new.sponsorship.wizard._get_offered_payment_modes).
        bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.web_company.id)], limit=1
        )
        if not bank_journal or not cls.env["account.journal"].search_count(
            [("type", "=", "sale"), ("company_id", "=", cls.web_company.id)]
        ):
            # This module is shared, and the checkout is only walkable where
            # the MyCompassion website's own company can invoice. Skipped
            # rather than failed on an instance where it cannot.
            raise unittest.SkipTest(
                "the MyCompassion website's company has no accounting set up"
            )
        if not cls.env["account.payment.method"].search(
            [("code", "=", "none"), ("payment_type", "=", "inbound")]
        ):
            cls.env["account.payment.method"].sudo().create(
                {"name": "Demo", "code": "none", "payment_type": "inbound"}
            )
        cls.provider = cls.env["payment.provider"].create(
            {
                "name": "Route Walk Provider",
                "code": "none",
                "company_id": cls.web_company.id,
                "journal_id": bank_journal.id,
                "state": "test",
            }
        )
        cls.provider._ensure_payment_method_line()
        cls.digital_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Route Walk Card",
                "company_id": cls.web_company.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": cls.provider.id,
                "is_published": True,
            }
        )

    def setUp(self):
        super().setUp()
        # An available, unreserved child: wizard_start refuses anything else,
        # and a leftover reservation would send it to the "child unavailable"
        # page instead of the checkout.
        self.child = self.env["compassion.child"].search(
            [("state", "in", self.env["compassion.child"]._available_states())],
            limit=1,
        )
        self.assertTrue(self.child, "the database needs an available child")
        self.child.write(
            {"website_reservation_date": False, "website_reservation_id": False}
        )
        # child_sponsored drives the GMC hold state, which the routes under
        # test have no part in. Outgoing GMC messages are stubbed for the same
        # reason: the payment page puts the contract in "waiting", which
        # queues one, and queue_job runs inline in tests - so it would leave
        # this walking through the routes to the point of calling out to
        # Compassion International.
        for model, method, stub in (
            ("compassion.child", "child_sponsored", lambda records, sponsor_id: None),
            ("gmc.message", "_perform_outgoing_action", lambda records: None),
        ):
            patcher = patch.object(self.registry[model], method, stub)
            patcher.start()
            self.addCleanup(patcher.stop)

    # === Helpers ===

    def _start_checkout(self, sponsorship_type="standard"):
        """GET the wizard page and return (csrf_token, wizard_id)."""
        page = self.url_open(
            f"/my2/new-sponsorship/{self.child.id}"
            f"?sponsorship_type={sponsorship_type}"
        )
        self.assertEqual(page.status_code, 200)
        csrf = CSRF_RE.search(page.text)
        wizard_id = WIZARD_ID_RE.search(page.text)
        self.assertTrue(csrf, "the wizard form should carry a csrf token")
        self.assertTrue(wizard_id, "the wizard form should carry its wizard id")
        return page.text, csrf.group(1), int(wizard_id.group(1))

    def _step(self, wizard_id, **post):
        return self.make_jsonrpc_request(
            "/my2/new-sponsorship/step", {"wizard_id": wizard_id, **post}
        )

    def _submit(self, csrf, wizard_id):
        return self.url_open(
            "/my2/new-sponsorship/submit",
            data={"csrf_token": csrf, "wizard_id": wizard_id},
            allow_redirects=False,
        )

    def _pay_first_page(self):
        """Walk the standard checkout up to the payment page.

        Returns the payment page's response and the signup it belongs to, in
        the session that went through the checkout - which is what the later
        thank-you assertions are about.
        """
        _html, csrf, wizard_id = self._start_checkout()
        self.assertEqual(
            self._step(
                wizard_id,
                email="route-walk@example.org",
                privacy_consent="true",
                payment_method=str(self.digital_mode.id),
                action="next",
            ),
            {"finish": True},
        )
        response = self._submit(csrf, wizard_id)
        self.assertEqual(response.status_code, 303)
        location = response.headers["Location"]
        self.assertIn("/my2/new-sponsorship/payment", location)
        signup = self.env["recurring.contract"].search(
            [("child_id", "=", self.child.id)], order="id desc", limit=1
        )
        self.assertTrue(signup, "the submit route should have created the signup")
        return location, signup

    def _open_in_a_fresh_session(self, url):
        """GET url as a visitor who has no session with this server yet.

        Same cursor, new cookie jar: a second browser looking at the same
        page, which is what the session-scoped part of the details gate is
        there to keep out.
        """
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            return self.url_open(url)
        finally:
            self.opener = own_opener

    # === /my2/new-sponsorship/<child> ===

    def test_wizard_page_serves_the_one_page_checkout(self):
        html, _csrf, wizard_id = self._start_checkout()
        self.assertIn('name="email"', html)
        self.assertIn('name="privacy_consent"', html)
        self.assertIn(f'data-payment-mode="{self.digital_mode.id}"', html)
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        # the wizard belongs to the website's company, not to whoever the
        # test happens to run as
        self.assertEqual(wizard.company_id, self.web_company)
        self.assertTrue(wizard.user_id._is_public())

    def test_wizard_page_refuses_an_unavailable_child(self):
        sponsored = self.env["compassion.child"].search(
            [("state", "not in", self.env["compassion.child"]._available_states())],
            limit=1,
        )
        self.assertTrue(sponsored, "the database needs an unavailable child")
        page = self.url_open(f"/my2/new-sponsorship/{sponsored.id}")
        self.assertEqual(page.status_code, 404)

    # === /my2/new-sponsorship/step ===

    def test_step_route_returns_the_next_page_then_finishes(self):
        _html, _csrf, wizard_id = self._start_checkout("write_and_pray")
        # Write&Pray keeps a second step, so the first one comes back as html
        result = self._step(
            wizard_id,
            email="route-walk-wap@example.org",
            privacy_consent="true",
            sponsorship_type="write_and_pray",
            action="next",
        )
        self.assertIn("html", result)
        self.assertNotIn("finish", result)
        # the standard flow is the one page, so its own step call finishes
        _html, _csrf, standard_id = self._start_checkout()
        self.assertEqual(
            self._step(
                standard_id,
                email="route-walk-standard@example.org",
                privacy_consent="true",
                payment_method=str(self.digital_mode.id),
                action="next",
            ),
            {"finish": True},
        )

    def test_step_route_refuses_an_unknown_wizard(self):
        with self.assertRaises(JsonRpcException):
            self._step(0, action="next")

    # === /my2/new-sponsorship/submit ===

    def test_submit_creates_the_signup_and_sends_it_to_pay(self):
        location, signup = self._pay_first_page()
        self.assertIn(f"sponsorship_id={signup.id}", location)
        # the redirect carries the token the payment page is guarded by
        self.assertIn("access_token=", location)
        self.assertEqual(signup.payment_mode_id, self.digital_mode)
        self.assertTrue(signup.my2_signup)
        # nothing but an email was asked for, so the sponsor is a placeholder
        self.assertTrue(signup.partner_id.my2_name_placeholder)
        self.assertEqual(signup.partner_id.email, "route-walk@example.org")

    def test_submit_refuses_an_unknown_wizard(self):
        _html, csrf, _wizard_id = self._start_checkout()
        self.assertEqual(self._submit(csrf, 0).status_code, 400)

    def test_submit_refuses_a_checkout_without_consent(self):
        """The tick is required in the page, and a posted form is not a page."""
        _html, csrf, wizard_id = self._start_checkout()
        self.assertEqual(
            self._step(
                wizard_id,
                email="route-walk-no-consent@example.org",
                payment_method=str(self.digital_mode.id),
                action="next",
            ),
            {"finish": True},
        )
        # the guard raises a ValidationError, which an http route answers with
        # a 400 - the same answer a tampered wizard id gets, deliberately
        response = self._submit(csrf, wizard_id)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            self.env["recurring.contract"].search_count(
                [("partner_id.email", "=", "route-walk-no-consent@example.org")]
            )
        )

    # === /my2/new-sponsorship/payment and /transaction ===

    def test_payment_page_is_served_to_the_signed_link_only(self):
        location, signup = self._pay_first_page()
        # The page generates this itself, and is asked for it here so that it
        # happens on the test's own cursor: putting the contract in "waiting"
        # reaches through invoicing into the GMC connector, which the
        # digital-seam suite covers and which has no business holding up a
        # routing test.
        invoice = signup._ensure_first_invoice()
        self.assertTrue(invoice)
        page = self.url_open(location)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Almost there", page.text)
        self.assertIn(f"{invoice.amount_residual:.2f}", page.text)
        # The step bar of a page that no longer knows its own step count:
        # since the fast checkout it is computed from the flow, and the public
        # standard flow is exactly one step, so this last one is it. Hard-coded
        # to 3 before T3365, which would draw three markers here.
        self.assertEqual(page.text.count("step-marker-container"), 1)
        # the id alone opens nothing: the token is the whole guard
        bare = self.url_open(f"/my2/new-sponsorship/payment?sponsorship_id={signup.id}")
        self.assertEqual(bare.status_code, 404)
        wrong = self.url_open(
            f"/my2/new-sponsorship/payment?sponsorship_id={signup.id}"
            "&access_token=not-the-token"
        )
        self.assertEqual(wrong.status_code, 404)

    def test_transaction_route_refuses_a_wrong_token(self):
        _location, signup = self._pay_first_page()
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f"/my2/new-sponsorship/transaction/{signup.id}",
                {"access_token": "not-the-token"},
            )

    def test_transaction_route_refuses_a_saved_card_to_the_public(self):
        """A public visitor is matched by email, which must never hand them
        someone else's stored instrument."""
        location, signup = self._pay_first_page()
        token = ACCESS_TOKEN_RE.search(location).group(1)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f"/my2/new-sponsorship/transaction/{signup.id}",
                {"access_token": token, "flow": "token"},
            )

    # === /my2/new-sponsorship/thank-you ===

    def test_thank_you_offers_the_form_to_the_session_that_paid(self):
        """No token in the URL, and the form is still there: the session the
        checkout ran in is the proof the sponsor came back from the gateway.
        """
        _location, signup = self._pay_first_page()
        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={signup.id}"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn("/my2/new-sponsorship/complete-details", page.text)
        self.assertIn("Who shall we thank?", page.text)

    def test_thank_you_offers_no_form_to_a_stranger(self):
        """The gate of the whole details flow: a bare sponsorship id proves
        nothing, so a visitor who did not go through this checkout must be
        given neither the form nor a token - the form is a write endpoint on
        someone else's partner record.
        """
        _location, signup = self._pay_first_page()
        page = self._open_in_a_fresh_session(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={signup.id}"
        )
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("/my2/new-sponsorship/complete-details", page.text)
        self.assertNotIn("/my2/new-sponsorship/details-later", page.text)
        # and no token was minted on the way out either
        self.assertFalse(signup.my2_details_token)

    def test_thank_you_refuses_an_unknown_signup(self):
        missing_id = (
            self.env["recurring.contract"].search([], order="id desc")[:1].id + 1
        )
        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={missing_id}"
        )
        self.assertEqual(page.status_code, 404)
        self.assertEqual(
            self.url_open("/my2/new-sponsorship/thank-you").status_code, 404
        )
