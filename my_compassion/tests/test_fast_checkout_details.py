import re
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .common import DigitalSeamCase

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
TOKEN_IN_LINK_RE = re.compile(r"details_token=([A-Za-z0-9_-]+)")


@tagged("post_install", "-at_install")
class TestFastCheckoutDetails(HttpCase, DigitalSeamCase):
    """The post-payment details form: the fast checkout's other half.

    Its POST route is a write endpoint on a public URL, so most of what is
    tested here is what it refuses.
    """

    def setUp(self):
        super().setUp()
        self.signup = self._make_pending_signup()

    def _make_pending_signup(self, email="fast-checkout-details@example.org"):
        """A confirmed signup still waiting for its sponsor's name."""
        contract = self._make_digital_contract()
        contract.my2_signup = True
        contract.partner_id.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": email,
                "phone": False,
            }
        )
        return contract

    def _thank_you_url(self, sponsorship=None, token=None, **params):
        sponsorship = sponsorship or self.signup
        url = f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        if token:
            url += f"&details_token={token}"
        for key, value in params.items():
            url += f"&{key}={value}"
        return url

    def _open_form(self, sponsorship=None, token=None):
        """Render the details form and return (html, csrf_token)."""
        page = self.url_open(self._thank_you_url(sponsorship, token))
        self.assertEqual(page.status_code, 200)
        csrf = CSRF_RE.search(page.text)
        self.assertTrue(csrf, "the details form should carry a csrf token")
        return page.text, csrf.group(1)

    def _post_details(self, csrf, sponsorship=None, token=None, **fields_):
        values = {
            "csrf_token": csrf,
            "sponsorship_id": (sponsorship or self.signup).id,
            "firstname": "Jeanne",
            "lastname": "Dupont",
            "phone": "+41 79 123 45 67",
        }
        values.update(fields_)
        if token is not None:
            values["details_token"] = token
        return self.url_open(
            "/my2/new-sponsorship/complete-details",
            data=values,
            allow_redirects=False,
        )

    # === The form on the thank-you page ===

    def test_form_offered_only_while_details_are_pending(self):
        token = self.signup._my2_issue_details_token()
        html, _csrf = self._open_form(token=token)
        self.assertIn("/my2/new-sponsorship/complete-details", html)
        self.assertIn("Who shall we thank?", html)
        # the escape hatch is on the same form
        self.assertIn("/my2/new-sponsorship/details-later", html)
        # once the name is real the page falls back to its normal content
        self.signup.partner_id._my2_replace_placeholder_name("Real", "Sponsor")
        page = self.url_open(self._thank_you_url(token=token))
        self.assertNotIn("/my2/new-sponsorship/complete-details", page.text)
        self.assertIn("Thank you for sponsoring", page.text)

    def test_form_prefills_the_cardholder_name(self):
        invoice = self.signup._ensure_first_invoice()
        self.env["payment.transaction"].create(
            {
                "provider_id": self.signup.payment_mode_id.payment_provider_id.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": self.signup.partner_id.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "fast-checkout-details-prefill",
                "operation": "online_direct",
                "invoice_ids": [(6, 0, invoice.ids)],
                "my2_cardholder_name": "Jean Michel Dupont",
            }
        )
        prefill = self.signup._my2_details_prefill()
        self.assertEqual(prefill["firstname"], "Jean Michel")
        self.assertEqual(prefill["lastname"], "Dupont")
        # a provider never reports a phone number
        self.assertFalse(prefill["phone"])
        html, _csrf = self._open_form(token=self.signup._my2_issue_details_token())
        self.assertIn('value="Jean Michel"', html)
        self.assertIn('value="Dupont"', html)

    def test_page_reload_keeps_the_emailed_link_alive(self):
        """Re-minting on every render would kill the link just mailed out."""
        token = self.signup._my2_issue_details_token(
            hours=self.signup.DETAILS_TOKEN_EMAIL_HOURS
        )
        self.assertEqual(self.signup._my2_ensure_details_token(), token)
        self.assertTrue(self.signup._my2_check_details_token(token))
        # an expired one is replaced, though
        self.signup.my2_details_token_expiration = fields.Datetime.now() - timedelta(
            minutes=1
        )
        self.assertNotEqual(self.signup._my2_ensure_details_token(), token)

    # === The write endpoint ===

    def test_details_are_saved_and_the_token_is_burnt(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        response = self._post_details(
            csrf,
            token=token,
            street="Rue du Test 1",
            zip="1000",
            city="Lausanne",
            country=self.env.ref("base.ch").id,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={self.signup.id}",
            response.headers["Location"],
        )
        partner = self.signup.partner_id
        self.assertEqual(partner.firstname, "Jeanne")
        self.assertEqual(partner.lastname, "Dupont")
        # Some country modules (e.g. Switzerland's partner_compassion) refile
        # a mobile-looking number from phone to mobile on write - the shared
        # module only cares that the submitted number landed somewhere.
        self.assertIn("+41 79 123 45 67", (partner.phone, partner.mobile))
        self.assertEqual(partner.street, "Rue du Test 1")
        self.assertEqual(partner.zip, "1000")
        self.assertEqual(partner.city, "Lausanne")
        self.assertEqual(partner.country_id, self.env.ref("base.ch"))
        self.assertFalse(partner.my2_name_placeholder)
        self.assertFalse(self.signup._my2_check_details_token(token))
        self.assertFalse(self.signup.my2_details_token)

    def test_address_stays_optional(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        response = self._post_details(csrf, token=token)
        self.assertEqual(response.status_code, 303)
        self.assertFalse(self.signup.partner_id.my2_name_placeholder)
        self.assertFalse(self.signup.partner_id.street)

    def test_missing_required_field_keeps_the_form_and_the_token(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        response = self._post_details(csrf, token=token, phone="  ")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my2/new-sponsorship/complete-details", response.text)
        # what was typed comes back, the placeholder stays, the token lives on
        self.assertIn('value="Jeanne"', response.text)
        self.assertTrue(self.signup.partner_id.my2_name_placeholder)
        self.assertTrue(self.signup._my2_check_details_token(token))

    def test_no_token_is_refused(self):
        _html, csrf = self._open_form(token=self.signup._my2_issue_details_token())
        response = self._post_details(csrf, token=None)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.signup.partner_id.my2_name_placeholder)

    def test_wrong_token_is_refused(self):
        _html, csrf = self._open_form(token=self.signup._my2_issue_details_token())
        response = self._post_details(csrf, token="not-the-token")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.signup.partner_id.my2_name_placeholder)

    def test_expired_token_is_refused(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        self.signup.my2_details_token_expiration = fields.Datetime.now() - timedelta(
            minutes=1
        )
        response = self._post_details(csrf, token=token)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.signup.partner_id.my2_name_placeholder)

    def test_replayed_token_is_refused(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        self.assertEqual(self._post_details(csrf, token=token).status_code, 303)
        replay = self._post_details(
            csrf, token=token, firstname="Someone", lastname="Else"
        )
        self.assertEqual(replay.status_code, 404)
        self.assertEqual(self.signup.partner_id.firstname, "Jeanne")

    def test_another_signups_token_is_refused(self):
        other = self._make_pending_signup(email="fast-checkout-other@example.org")
        other_token = other._my2_issue_details_token()
        _html, csrf = self._open_form(token=self.signup._my2_issue_details_token())
        # a token minted for one signup must not open another
        response = self._post_details(csrf, token=other_token)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.signup.partner_id.my2_name_placeholder)
        self.assertTrue(other.partner_id.my2_name_placeholder)

    def test_unknown_signup_is_refused(self):
        _html, csrf = self._open_form(token=self.signup._my2_issue_details_token())
        missing_id = (
            self.env["recurring.contract"].search([], order="id desc")[:1].id + 1
        )
        response = self.url_open(
            "/my2/new-sponsorship/complete-details",
            data={
                "csrf_token": csrf,
                "sponsorship_id": missing_id,
                "details_token": "whatever",
                "firstname": "Jeanne",
                "lastname": "Dupont",
                "phone": "+41 79 123 45 67",
            },
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 404)

    # === "Do this later - we will email you" ===

    def test_details_later_emails_a_working_link(self):
        token = self.signup._my2_issue_details_token()
        _html, csrf = self._open_form(token=token)
        response = self.url_open(
            "/my2/new-sponsorship/details-later",
            data={
                "csrf_token": csrf,
                "sponsorship_id": self.signup.id,
                "details_token": token,
            },
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("details_emailed=1", response.headers["Location"])
        job = self.env["partner.communication.job"].search(
            [
                ("config_id", "=", self.signup._my2_details_reminder_config().id),
                ("partner_id", "=", self.signup.partner_id.id),
            ]
        )
        self.assertEqual(len(job), 1)
        self.assertTrue(job.auto_send)
        # the mailed token is a fresh, longer-lived one, and it works
        mailed = TOKEN_IN_LINK_RE.search(job.body_html)
        self.assertTrue(mailed, "the email should carry a details link")
        mailed_token = mailed.group(1)
        self.assertNotEqual(mailed_token, token)
        self.assertTrue(self.signup._my2_check_details_token(mailed_token))
        self.assertFalse(self.signup._my2_check_details_token(token))
        self.assertGreater(
            self.signup.my2_details_token_expiration,
            fields.Datetime.now() + timedelta(hours=self.signup.DETAILS_TOKEN_HOURS),
        )
        # the page the sponsor is left on no longer offers the form, so
        # rendering it cannot re-mint over the token just mailed
        page = self.url_open(self._thank_you_url(details_emailed=1))
        self.assertNotIn("/my2/new-sponsorship/complete-details", page.text)
        self.assertTrue(self.signup._my2_check_details_token(mailed_token))
        # and the emailed link lands back on the form
        html, _csrf = self._open_form(token=mailed_token)
        self.assertIn("/my2/new-sponsorship/complete-details", html)

    def test_details_later_needs_a_token(self):
        """Otherwise the route would mail any sponsor whose id is guessed."""
        _html, csrf = self._open_form(token=self.signup._my2_issue_details_token())
        response = self.url_open(
            "/my2/new-sponsorship/details-later",
            data={"csrf_token": csrf, "sponsorship_id": self.signup.id},
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            self.env["partner.communication.job"].search_count(
                [("partner_id", "=", self.signup.partner_id.id)]
            )
        )

    def test_details_reminder_needs_an_email_on_file(self):
        self.signup.partner_id.email = False
        self.assertFalse(self.signup._my2_send_details_reminder())
        # and nothing is mailed once the details are in either
        self.signup.partner_id.write(
            {
                "email": "fast-checkout-noemail@example.org",
                "my2_name_placeholder": False,
            }
        )
        self.assertFalse(self.signup._my2_send_details_reminder())
