import re
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    HttpCase,
    JsonRpcException,
    Opener,
)

from ..controllers.my2_sponsorships import WIZARD_TOKENS_SESSION_KEY
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
        #
        # Forced into that state rather than searched for: which states an
        # instance's own child data happens to sit in is exactly the kind of
        # thing this test must not depend on (a database can legitimately
        # have every real child already reserved or sponsored), and every
        # other fixture in this suite already picks "any child" the same
        # unfiltered way - only its availability is this test's own concern.
        self.child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(self.child, "the database needs a child")
        self.child.write(
            {
                "state": self.env["compassion.child"]._available_states()[0],
                "website_reservation_date": False,
                "website_reservation_id": False,
            }
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
            f"/my2/new-sponsorship/{self.child.id}?sponsorship_type={sponsorship_type}"
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

    @contextmanager
    def _in_another_browser(self):
        """Every request in the block comes from a second browser, with a
        session of its own: another visitor, as far as the server can tell.
        """
        own_opener = self.opener
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = own_opener.cookies[
            TEST_CURSOR_COOKIE_NAME
        ]
        try:
            yield
        finally:
            self.opener = own_opener

    def _another_child(self):
        """A second available child, for a visitor who needs a checkout of
        their own (its page is where their csrf token comes from)."""
        child = self.env["compassion.child"].search(
            [("id", "!=", self.child.id)], limit=1
        )
        self.assertTrue(child, "the database needs a second child")
        child.write(
            {
                "state": self.env["compassion.child"]._available_states()[0],
                "website_reservation_date": False,
                "website_reservation_id": False,
            }
        )
        return child

    def _start_checkout_of(self, child):
        own_child = self.child
        self.child = child
        try:
            return self._start_checkout()
        finally:
            self.child = own_child

    def _answer(self, wizard_id, email, **post):
        """The one page of the standard checkout, answered."""
        return self._step(
            wizard_id,
            email=email,
            privacy_consent="true",
            payment_method=str(self.digital_mode.id),
            action="next",
            **post,
        )

    def _signups_of(self, email):
        return self.env["recurring.contract"].search_count(
            [("partner_id.email", "=", email)]
        )

    def _portal_user(self, login):
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "password": login,
                    "email": f"{login}@example.org",
                    "groups_id": [Command.set([self.env.ref("base.group_portal").id])],
                }
            )
        )

    def _assert_untouched(self, wizard, email):
        """The wizard is as its owner left it, and finished nothing."""
        wizard.invalidate_recordset()
        self.assertEqual(wizard.email, email)
        self.assertFalse(wizard.sponsorship_id)

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
        self.assertEqual(self._submit(csrf, 0).status_code, 404)

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
        # The payment page dropped its progress bar: it is the last step
        # before the thank-you page, and the title/description already say
        # "you're almost there" - a marker count would only repeat that.
        self.assertEqual(page.text.count("step-marker-container"), 0)
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
        self.assertEqual(page.status_code, 404)
        # no token was minted on the way out either
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

    # === failed first payment ===

    def _first_payment(self, signup, state):
        """A first-payment transaction of the signup ended in state."""
        invoice = signup._ensure_first_invoice()
        self.assertTrue(invoice)
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": self.provider.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "partner_id": signup.partner_id.id,
                "reference": f"route-walk-first-payment-{state}",
                "invoice_ids": [(6, 0, invoice.ids)],
            }
        )
        if state == "cancel":
            tx._set_canceled()
        elif state == "error":
            tx._set_error("declined")
        elif state == "done":
            tx._set_done()
        return tx

    def test_thank_you_sends_a_failed_payment_back_to_pay(self):
        """The gateway lands on the thank-you page even when the payment
        failed: the sponsor is sent back to pay, with another card."""
        _location, signup = self._pay_first_page()
        for state in ("cancel", "error"):
            with self.subTest(state=state):
                self._first_payment(signup, state)
                page = self.url_open(
                    f"/my2/new-sponsorship/thank-you?sponsorship_id={signup.id}",
                    allow_redirects=False,
                )
                self.assertEqual(page.status_code, 303)
                location = page.headers["Location"]
                self.assertIn("/my2/new-sponsorship/payment", location)
                self.assertIn("payment_failed=1", location)
                retry = self.url_open(location)
                self.assertEqual(retry.status_code, 200)
                self.assertIn("Your payment did not go through", retry.text)

    def test_thank_you_after_a_successful_payment(self):
        _location, signup = self._pay_first_page()
        self._first_payment(signup, "cancel")
        # the retry went through
        self._first_payment(signup, "done")
        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={signup.id}",
            allow_redirects=False,
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn("Who shall we thank?", page.text)

    def test_payment_page_shows_no_failure_without_one(self):
        """payment_failed in the URL alone does not show the message."""
        location, signup = self._pay_first_page()
        signup._ensure_first_invoice()
        page = self.url_open(f"{location}&payment_failed=1")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("Your payment did not go through", page.text)

    # === Wizards belong to the browser session that started them ===

    def test_another_visitor_cannot_use_the_wizard(self):
        """Wizard ids are sequential and sent in the page, and every
        anonymous visitor is the same public user: the id alone must not let
        another visitor read, change or finish someone else's checkout."""
        _html, _csrf, wizard_id = self._start_checkout()
        self._step(wizard_id, email="owner@example.org")
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        self.assertTrue(wizard.session_token)
        with self._in_another_browser():
            # their own checkout, for a valid csrf token of their session
            _html, other_csrf, _other_id = self._start_checkout_of(
                self._another_child()
            )
            # reading the page back is a step without an action
            with self.assertRaises(JsonRpcException):
                self._step(wizard_id)
            with self.assertRaises(JsonRpcException):
                self._answer(wizard_id, "intruder@example.org")
            self.assertEqual(self._submit(other_csrf, wizard_id).status_code, 404)
        self._assert_untouched(wizard, "owner@example.org")
        self.assertEqual(wizard.current_step_idx, 0)
        self.assertFalse(self._signups_of("intruder@example.org"))
        # the owner still goes through
        self.assertEqual(self._answer(wizard_id, "owner@example.org"), {"finish": True})

    def test_another_user_cannot_use_the_wizard(self):
        """Same separation between two logged-in sponsors, and the token
        alone is not enough either: it must come with the user who started
        the wizard."""
        anna = self._portal_user("wizard-owner-anna")
        jan = self._portal_user("wizard-owner-jan")
        self.authenticate(anna.login, anna.login)
        _html, _csrf, wizard_id = self._start_checkout()
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        self.assertEqual(wizard.user_id, anna)
        self._step(wizard_id, email="anna@example.org")
        # Jan's own session, even holding Anna's token
        self.authenticate(
            jan.login,
            jan.login,
            session_extra={
                WIZARD_TOKENS_SESSION_KEY: {str(wizard_id): wizard.session_token}
            },
        )
        _html, jan_csrf, _jan_id = self._start_checkout_of(self._another_child())
        with self.assertRaises(JsonRpcException):
            self._step(wizard_id)
        with self.assertRaises(JsonRpcException):
            self._step(wizard_id, email="jan@example.org", action="next")
        self.assertEqual(self._submit(jan_csrf, wizard_id).status_code, 404)
        self._assert_untouched(wizard, "anna@example.org")
        self.assertEqual(wizard.current_step_idx, 0)

    def test_a_session_without_the_token_is_refused(self):
        """A session that expired, or never had the token, starts over: it
        is refused before anything is read or written."""
        _html, _csrf, wizard_id = self._start_checkout()
        self._step(wizard_id, email="expired@example.org")
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        for tokens in ({}, {str(wizard_id): "not-the-token"}):
            with self.subTest(tokens=tokens):
                self.authenticate(
                    None, None, session_extra={WIZARD_TOKENS_SESSION_KEY: tokens}
                )
                with self.assertRaises(JsonRpcException):
                    self._answer(wizard_id, "someone-else@example.org")
                self._assert_untouched(wizard, "expired@example.org")
                self.assertEqual(wizard.current_step_idx, 0)

    def test_a_wizard_not_at_its_last_step_cannot_finish(self):
        _html, csrf, wizard_id = self._start_checkout()
        email = "route-walk-early@example.org"
        # every answer given, but the page was never submitted forward
        self._step(
            wizard_id,
            email=email,
            privacy_consent="true",
            payment_method=str(self.digital_mode.id),
        )
        self.assertEqual(self._submit(csrf, wizard_id).status_code, 400)
        self.assertFalse(self._signups_of(email))
        # and it is the last-step check that refused it, not another one
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        self.assertFalse(wizard.is_done)
        with self.assertRaisesRegex(ValidationError, "complete every step"):
            wizard.finish_sponsorship()
        self.assertFalse(self._signups_of(email))

    def test_a_child_reserved_by_another_session_cannot_finish(self):
        """The reservation lasts a few minutes: a checkout left open longer
        must not finish on a child another visitor reserved since."""
        _html, csrf, wizard_id = self._start_checkout()
        email = "route-walk-late@example.org"
        self.assertEqual(self._answer(wizard_id, email), {"finish": True})
        self.child.write(
            {
                "website_reservation_date": fields.Datetime.now(),
                "website_reservation_id": "another-session",
            }
        )
        response = self._submit(csrf, wizard_id)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Good news!", response.text)
        self.assertFalse(self._signups_of(email))
        # the model refuses it too, whoever calls it
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        with self.assertRaisesRegex(ValidationError, "no longer available"):
            wizard.finish_sponsorship()

    def test_submitting_twice_creates_one_signup(self):
        """A double click: the second submit lands where the first did,
        without creating a second contract."""
        _html, csrf, wizard_id = self._start_checkout()
        email = "route-walk-twice@example.org"
        self.assertEqual(self._answer(wizard_id, email), {"finish": True})
        first = self._submit(csrf, wizard_id)
        second = self._submit(csrf, wizard_id)
        self.assertEqual(first.status_code, 303)
        self.assertEqual(second.status_code, 303)
        self.assertEqual(second.headers["Location"], first.headers["Location"])
        self.assertEqual(self._signups_of(email), 1)
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        self.assertTrue(wizard.sponsorship_id)
        # a used wizard has no step left, and never finishes again
        with self.assertRaises(JsonRpcException):
            self._step(wizard_id)
        with self.assertRaisesRegex(ValidationError, "already sent"):
            wizard.finish_sponsorship()
        self.assertEqual(self._signups_of(email), 1)

    def test_submit_without_online_payment_lands_on_the_thank_you(self):
        bank_mode = self.env["account.payment.mode"].create(
            {
                "name": "Route Walk Standing Order",
                "company_id": self.web_company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "is_published": True,
            }
        )
        _html, csrf, wizard_id = self._start_checkout()
        email = "route-walk-bank@example.org"
        self.assertEqual(
            self._step(
                wizard_id,
                email=email,
                privacy_consent="true",
                payment_method=str(bank_mode.id),
                action="next",
            ),
            {"finish": True},
        )
        response = self._submit(csrf, wizard_id)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/my2/new-sponsorship/thank-you", response.headers["Location"])
        self.assertEqual(self._signups_of(email), 1)

    def test_a_wizard_pointed_at_another_signup_opens_nothing(self):
        """The redirect of a second submit hands out the payment page's
        access token: a wizard whose sponsorship was set to someone else's
        contract must not turn into a way of getting that token."""
        _location, victim = self._pay_first_page()
        invoices_before = victim.invoice_line_ids.move_id
        # a fresh session, which never went through the victim's checkout
        self.authenticate(None, None)
        _html, csrf, wizard_id = self._start_checkout_of(self._another_child())
        wizard = self.env["new.sponsorship.wizard"].browse(wizard_id)
        # the field is closed to RPC: only admins (and sudo) may write it
        portal = self._portal_user("wizard-ownership-rpc")
        with self.assertRaises(AccessError):
            wizard.with_user(portal).write({"sponsorship_id": victim.id})
        # had it been written anyway, the submit would still open nothing
        wizard.sponsorship_id = victim
        response = self._submit(csrf, wizard_id)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("access_token", response.headers.get("Location", ""))
        self.assertNotIn("access_token", response.text)
        victim.invalidate_recordset()
        self.assertEqual(victim.invoice_line_ids.move_id, invoices_before)
