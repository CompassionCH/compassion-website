##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestLegalRoutes(HttpCase):
    """/legal leads to the privacy policy of the website and /legal/terms to
    its terms and conditions, when it has them apart."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        cls.website.privacy_policy_url = "https://example.org/privacy"

    def _location(self, url):
        response = self.url_open(url, allow_redirects=False)
        self.assertIn(response.status_code, (302, 303))
        return response.headers["Location"]

    def test_terms_apart(self):
        self.website.terms_url = "https://example.org/terms"
        self.assertEqual(self._location("/legal"), "https://example.org/privacy")
        self.assertEqual(self._location("/legal/terms"), "https://example.org/terms")

    def test_terms_on_the_single_legal_page(self):
        self.website.terms_url = False
        self.assertTrue(self._location("/legal/terms").endswith("/legal"))
