from datetime import datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

CONSENT_ERROR = "Please accept the terms and conditions and the privacy policy."
CONSENT_DATE = datetime(2025, 2, 3, 10, 11, 12)


@tagged("post_install", "-at_install")
class TestSignupConsent(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_website = cls.env.ref("website.default_website")
        cls.my2_website = cls.env.ref("my_compassion.my2_website")
        cls.second_portal = cls.env["website"].create(
            {
                "name": "Consent portal",
                "domain": "https://consent.example.org",
                "is_my_compassion": True,
                "company_id": cls.main_website.company_id.id,
                "auth_signup_uninvited": "b2c",
            }
        )
        cls.websites = cls.main_website | cls.my2_website | cls.second_portal
        cls.websites.write({"auth_signup_uninvited": "b2c"})
        cls.env["ir.config_parameter"].sudo().set_param(
            "auth_signup.reset_password", True
        )
        # The confirmation template renders on a communication job, whose
        # language belongs to its partner.
        cls.env.ref(
            "my_compassion.signup_confirmation_set_password_email"
        ).lang = "{{object.partner_id.lang}}"

    def setUp(self):
        super().setUp()
        self._select_website(self.main_website)
        # DNS and mail delivery are outside the consent boundary under test.
        for patcher in (
            patch(
                "odoo.addons.auth_signup_verify_email.controllers.main.validate_email"
            ),
            patch.object(self.registry["mail.mail"], "send", return_value=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _select_website(self, website):
        for other in self.websites:
            other.domain = f"https://consent-{other.id}.example.org"
        self.websites.flush_recordset(["domain"])
        website.domain = self.base_url()
        self.authenticate(None, None)

    def _checkboxes(self, response):
        self.assertEqual(response.status_code, 200, response.text[:500])
        return html.fromstring(response.content).xpath(
            '//input[@name="privacy_policy"]'
        )

    def _assert_checkbox(self, response, required=True):
        checkboxes = self._checkboxes(response)
        self.assertEqual(len(checkboxes), int(required))
        if required:
            self.assertEqual(checkboxes[0].get("type"), "checkbox")
            self.assertEqual(checkboxes[0].get("value"), "accepted")
            self.assertIsNotNone(checkboxes[0].get("required"))

    def _post(self, values, path="/web/signup", token=None, session_token=False):
        query = "?" + urlencode({"token": token}) if token else ""
        if session_token:
            self.authenticate(None, None, session_extra={"auth_signup_token": token})
            query = ""
        page = self.url_open(path + query, allow_redirects=False)
        # Invitations on the reset route redirect before rendering a form.
        if page.status_code in (302, 303):
            page = self.url_open(page.headers["Location"])
        csrf = html.fromstring(page.content).xpath('//input[@name="csrf_token"]/@value')
        self.assertTrue(csrf, page.text[:500])
        data = {"csrf_token": csrf[0], **values}
        if token and not session_token:
            data["token"] = token
        return self.url_open(path, data=data, allow_redirects=False)

    def _user(self, login):
        self.env.invalidate_all()
        return self.env["res.users"].sudo().search([("login", "=", login)])

    def _values(self, login, password=True):
        values = {"login": login, "name": "Consent signup"}
        if password:
            values.update(password="SignupTest42!", confirm_password="SignupTest42!")
        return values

    def _invitation(
        self, date=False, existing_user=False, signup_type="signup", login=None
    ):
        partner = self.env["res.partner"].create(
            {
                "name": "Invited sponsor",
                "email": login or "invited-consent@example.org",
                "legal_agreement_date": date,
            }
        )
        if existing_user:
            self.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": partner.name,
                    "login": partner.email,
                    "partner_id": partner.id,
                    "groups_id": [(6, 0, self.env.ref("base.group_portal").ids)],
                }
            )
        partner.signup_prepare(signup_type=signup_type)
        return partner, partner._generate_signup_token()

    def test_checkbox_on_every_website(self):
        for website in self.websites:
            with self.subTest(website=website.name):
                self._select_website(website)
                self._assert_checkbox(self.url_open("/web/signup"))

    def _check_submissions(self, password):
        login = f"consent-{'password' if password else 'email'}@example.org"
        values = self._values(login, password=password)
        for consent in (None, "wrong"):
            with self.subTest(consent=consent):
                refused_login = f"refused-{consent}-{login}"
                data = self._values(refused_login, password=password)
                if consent is not None:
                    data["privacy_policy"] = consent
                page = self._post(data)
                self.assertFalse(
                    self._user(refused_login), "Signup created a user without consent"
                )
                self.assertIn(CONSENT_ERROR, page.text)
                self._assert_checkbox(page)
                self.assertFalse(
                    self.env["res.partner"].search([("email", "=", refused_login)])
                )
        before = fields.Datetime.now()
        page = self._post({**values, "privacy_policy": "accepted"})
        self.assertLess(page.status_code, 400)
        user = self._user(login)
        self.assertEqual(len(user), 1, page.text[:500])
        self.assertTrue(user.partner_id.legal_agreement_date)
        self.assertGreaterEqual(user.partner_id.legal_agreement_date, before)
        self.assertLessEqual(user.partner_id.legal_agreement_date, datetime.now())

    def test_password_submissions(self):
        self._check_submissions(password=True)

    def test_passwordless_submissions(self):
        self._check_submissions(password=False)

    def test_passwordless_cannot_choose_consent_date(self):
        login = "forged-date-consent@example.org"
        before = fields.Datetime.now()
        page = self._post(
            {
                **self._values(login, password=False),
                "privacy_policy": "accepted",
                "legal_agreement_date": "2001-01-01 00:00:00",
            }
        )
        self.assertEqual(page.status_code, 200)
        user = self._user(login)
        self.assertEqual(len(user), 1)
        self.assertGreaterEqual(user.partner_id.legal_agreement_date, before)
        self.assertLessEqual(user.partner_id.legal_agreement_date, datetime.now())

    def test_passwordless_invitation_cannot_overwrite_consent(self):
        partner, token = self._invitation(date=CONSENT_DATE)
        page = self._post(
            {
                **self._values(partner.email, password=False),
                "legal_agreement_date": "2001-01-01 00:00:00",
            },
            token=token,
        )
        self.assertEqual(page.status_code, 200)
        user = self._user(partner.email)
        self.assertEqual(user.partner_id, partner)
        self.assertEqual(partner.legal_agreement_date, CONSENT_DATE)

    def test_passwordless_ignores_extra_partner_fields(self):
        login = "extra-fields-consent@example.org"
        page = self._post(
            {
                **self._values(login, password=False),
                "privacy_policy": "accepted",
                "street": "Client supplied street",
                "email": "client-chosen-email@example.org",
            }
        )
        self.assertEqual(page.status_code, 200)
        user = self._user(login)
        self.assertEqual(len(user), 1)
        self.assertFalse(user.partner_id.street)
        self.assertEqual(user.partner_id.email, login)

    def test_passwordless_keeps_recaptcha_verification(self):
        login = "captcha-consent@example.org"
        with patch.object(
            self.registry["ir.http"],
            "_verify_recaptcha_token",
            return_value="is_human",
        ) as verify:
            page = self._post(
                {
                    **self._values(login, password=False),
                    "privacy_policy": "accepted",
                    "recaptcha_token_response": "signup-captcha-token",
                }
            )
        self.assertEqual(page.status_code, 200)
        verify.assert_called_once_with("127.0.0.1", "signup-captcha-token", "signup")
        self.assertEqual(len(self._user(login)), 1)

    def test_passwordless_get_does_not_create_user(self):
        values = self._values("get-consent@example.org", password=False)
        page = self.url_open(
            "/web/signup?" + urlencode({**values, "privacy_policy": "accepted"})
        )
        self.assertFalse(self._user(values["login"]))
        self._assert_checkbox(page)

    def test_submitted_policy_cannot_exempt_signup(self):
        values = self._values("forged-consent@example.org")
        page = self._post({**values, "signup_consent_required": "false"})
        self.assertIn(CONSENT_ERROR, page.text)
        self.assertFalse(self._user(values["login"]))

    def test_invitation_requires_consent(self):
        partner, token = self._invitation()
        self._assert_checkbox(
            self.url_open("/web/signup?" + urlencode({"token": token}))
        )
        values = self._values(partner.email)
        for consent in (None, "wrong"):
            data = {**values, "privacy_policy": consent} if consent else values
            page = self._post(data, token=token)
            self.assertIn(CONSENT_ERROR, page.text)
            self.assertFalse(self._user(partner.email))
            self.assertFalse(partner.legal_agreement_date)
        self._post({**values, "privacy_policy": "accepted"}, token=token)
        user = self._user(partner.email)
        self.assertEqual(user.partner_id, partner)
        self.assertTrue(partner.legal_agreement_date)

    def test_existing_invitation_preserves_consent(self):
        partner, token = self._invitation(date=CONSENT_DATE, existing_user=True)
        self._assert_checkbox(
            self.url_open("/web/signup?" + urlencode({"token": token})), required=False
        )
        self._post(self._values(partner.email), token=token)
        self.assertTrue(self._user(partner.email))
        self.assertEqual(partner.legal_agreement_date, CONSENT_DATE)

    def test_session_invitation_requires_consent(self):
        partner, token = self._invitation(existing_user=True)
        self.authenticate(None, None, session_extra={"auth_signup_token": token})
        self._assert_checkbox(self.url_open("/web/signup"))
        page = self._post(self._values(partner.email), token=token, session_token=True)
        self.assertIn(CONSENT_ERROR, page.text)
        self.env.invalidate_all()
        self.assertFalse(partner.legal_agreement_date)
        self.assertEqual(partner.signup_type, "signup")
        self._post(
            {**self._values(partner.email), "privacy_policy": "accepted"},
            token=token,
            session_token=True,
        )
        self.env.invalidate_all()
        self.assertTrue(partner.legal_agreement_date)

    def test_reset_never_records_consent(self):
        for path, date in (
            ("/web/reset_password", CONSENT_DATE),
            ("/web/signup", False),
        ):
            with self.subTest(path=path):
                self.authenticate(None, None)
                partner, token = self._invitation(
                    date=date,
                    existing_user=True,
                    signup_type="reset",
                    login=f"reset-{bool(date)}@example.org",
                )
                self._assert_checkbox(
                    self.url_open(path + "?" + urlencode({"token": token})),
                    required=False,
                )
                values = self._values(partner.email)
                if not date:
                    values["privacy_policy"] = "accepted"
                page = self._post(values, path=path, token=token)
                self.assertLess(page.status_code, 400)
                self.env.invalidate_all()
                self.assertEqual(partner.legal_agreement_date, date)

    def test_invalid_token_cannot_create_user(self):
        for password in (False, True):
            values = self._values(f"invalid-{password}@example.org", password=password)
            page = self._post(
                {**values, "privacy_policy": "accepted"}, token="invalid-consent-token"
            )
            self.assertIn("Invalid signup token", page.text)
            self.assertFalse(self._user(values["login"]))

    def test_invitation_cannot_use_reset_route(self):
        partner, token = self._invitation()
        page = self.url_open(
            "/web/reset_password?" + urlencode({"token": token}), allow_redirects=False
        )
        self.assertIn(page.status_code, (302, 303))
        location = urlsplit(page.headers["Location"])
        self.assertEqual(location.path, "/web/signup")
        self.assertEqual(parse_qs(location.query)["token"], [token])
        page = self._post(
            {**self._values(partner.email), "privacy_policy": "accepted"},
            path="/web/reset_password",
            token=token,
        )
        self.assertEqual(page.status_code, 400)
        self.assertFalse(self._user(partner.email))
        self.assertFalse(partner.legal_agreement_date)


@tagged("post_install", "-at_install")
class TestSignupConsentPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.users = self.env["res.users"].with_context(no_reset_password=True)
        self.env["website"].search([]).auth_signup_uninvited = "b2c"

    def _signup(self, login, users=None):
        users = users if users is not None else self.users
        users.signup({"login": login, "name": "Consent model", "password": "Signup42!"})
        return self.users.search([("login", "=", login)])

    def test_backend_signup_does_not_invent_consent(self):
        user = self._signup("backend-consent@example.org")
        self.assertTrue(user)
        self.assertFalse(user.partner_id.legal_agreement_date)

    def test_consent_is_recorded_before_replacement_is_queued(self):
        def assert_consent(users, job_function, user_id, email, **kwargs):
            self.assertEqual(job_function, "_find_and_replace_partner_async")
            self.assertEqual(
                users.browse(user_id).partner_id.legal_agreement_date, CONSENT_DATE
            )

        with patch.object(self.registry["res.users"], "with_delay_sh", assert_consent):
            user = self._signup(
                "queued-consent@example.org",
                users=self.users.with_context(
                    my_compassion_signup_consent_at=CONSENT_DATE
                ),
            )
        self.assertEqual(user.partner_id.legal_agreement_date, CONSENT_DATE)

    def _replace_partner(self, destination_date=False):
        user = self._signup("replace-consent@example.org")
        old_partner = user.partner_id
        old_partner.legal_agreement_date = CONSENT_DATE
        destination = self.env["res.partner"].create(
            {
                "name": "Existing sponsor",
                "email": user.login,
                "legal_agreement_date": destination_date,
            }
        )
        self.users._find_and_replace_partner_async(user.id, user.login)
        self.assertEqual(user.partner_id, destination)
        self.assertFalse(old_partner.exists())
        return destination

    def test_replacement_carries_consent(self):
        self.assertEqual(self._replace_partner().legal_agreement_date, CONSENT_DATE)

    def test_replacement_keeps_existing_consent(self):
        earlier_date = datetime(2024, 1, 2, 9, 10, 11)
        self.assertEqual(
            self._replace_partner(earlier_date).legal_agreement_date, earlier_date
        )
