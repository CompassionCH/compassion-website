##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import HttpCase, tagged

from ..hooks import _apply_my2_theme

BOUND_KEYS = [
    "my_compassion.my2_login_template",
    "my_compassion.my2_login_form",
    "my_compassion.my2_signup_fields",
    "my_compassion.my2_signup_form",
    "my_compassion.my2_reset_password_form",
    "my_compassion.my2_change_password_fullpage",
    "my_compassion.my2_contactus_page",
    "my_compassion.child_protection_charter_page_override",
    "my_compassion.child_protection_charter_confirmation_page_override",
]


@tagged("post_install", "-at_install")
class TestMy2WebsiteViews(HttpCase):
    """A second MyCompassion website (e.g. Poland) gets the login, signup
    and consent views bound to the first one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.my2_website = cls.env.ref("my_compassion.my2_website")
        cls.website = cls.env["website"].create(
            {
                "name": "Second MyCompassion",
                "domain": cls.base_url(),
                "is_my_compassion": True,
                "auth_signup_uninvited": "b2c",
            }
        )
        # The first website shares the test domain otherwise.
        cls.my2_website.domain = "http://my2.example.com"
        # Its pages call the theme's components, as on Poland's website.
        _apply_my2_theme(cls.env)

    def _copies(self):
        return (
            self.env["ir.ui.view"]
            .with_context(active_test=False)
            .search([("key", "in", BOUND_KEYS), ("website_id", "=", self.website.id)])
        )

    def test_bound_views_copied(self):
        copies = self._copies()
        self.assertEqual(set(copies.mapped("key")), set(BOUND_KEYS))
        for copy in copies:
            original = self.env.ref(copy.key)
            self.assertEqual(copy.inherit_id.key, original.inherit_id.key)
            self.assertEqual(copy.arch, original.arch)
            # Not the module's record: a copy the update refreshes.
            self.assertNotEqual(copy.xml_id, copy.key)

    def test_copied_once(self):
        self.website._configure_my_compassion_portal()
        self.assertEqual(len(self._copies()), len(BOUND_KEYS))

    def test_signup_asks_the_consent(self):
        page = self.url_open("/web/signup").text
        self.assertIn('name="privacy_policy"', page)
        self.assertIn('class="acceptance_full"', page)
