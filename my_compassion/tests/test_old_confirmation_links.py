##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from urllib.parse import parse_qs, urlparse

from odoo.tests import HttpCase, new_test_user, tagged

OLD_LINKS = (
    "/child/238965/sponsor/confirmation?face_reveal=1",
    "/child/238965/confirmation",
)


@tagged("post_install", "-at_install")
class TestOldConfirmationLinks(HttpCase):
    """Links to the MyCompassion 1.0 confirmation page, still in e-mails
    already sent, take the sponsor to their children, after login."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        # in the website language, so no language redirect comes first
        new_test_user(
            cls.env,
            login="old_link_sponsor",
            groups="base.group_portal",
            lang=cls.website.default_lang_id.code,
        )

    def _location(self, url):
        response = self.url_open(url, allow_redirects=False)
        self.assertIn(response.status_code, (302, 303))
        return urlparse(response.headers["Location"])

    def test_logged_out_goes_through_login(self):
        for url in OLD_LINKS:
            with self.subTest(url=url):
                location = self._location(url)
                self.assertEqual(location.path, "/web/login")
                redirect = parse_qs(location.query)["redirect"][0]
                self.assertEqual(urlparse(redirect).path, url.split("?")[0])
                # after login, the same link leads to the children
                self.authenticate("old_link_sponsor", "old_link_sponsor")
                self.assertEqual(self._location(url).path, "/my2/children")
                self.logout()

    def test_logged_in_goes_to_children(self):
        self.authenticate("old_link_sponsor", "old_link_sponsor")
        for url in OLD_LINKS:
            with self.subTest(url=url):
                self.assertEqual(self._location(url).path, "/my2/children")
