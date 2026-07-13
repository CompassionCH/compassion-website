##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import TransactionCase, tagged

DYNAMIC_STYLESHEET_URLS = [
    "/theme_compassion_2025/dynamic/colors.scss",
    "/theme_compassion_2025/dynamic/pictograms.scss",
    "/theme_compassion_2025/dynamic/icons.scss",
    "/theme_compassion_2025/dynamic/palette.scss",
]


@tagged("post_install", "-at_install")
class TestThemeAutoApply(TransactionCase):
    """The MyCompassion website must be usable right after module install:
    the theme applied without any UI step and every asset bundle input
    resolvable regardless of the current website.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.theme = cls.env["ir.module.module"].search(
            [("name", "=", "theme_compassion_2025")], limit=1
        )

    def test_theme_bound_to_my2_website(self):
        self.assertEqual(
            self.website.theme_id,
            self.theme,
            "theme_compassion_2025 must be applied to the MyCompassion "
            "website by the post_init hook",
        )

    def test_theme_views_instantiated(self):
        views = self.env["ir.ui.view"].search_count(
            [
                ("website_id", "=", self.website.id),
                ("theme_template_id", "!=", False),
            ]
        )
        self.assertTrue(
            views,
            "the theme's view masters must be instantiated for the "
            "MyCompassion website",
        )

    def test_dynamic_stylesheets_resolve_without_website(self):
        attachment_model = self.env["ir.attachment"].sudo()
        for url in DYNAMIC_STYLESHEET_URLS:
            attachment = attachment_model._get_serve_attachment(url)
            self.assertTrue(
                attachment,
                f"{url} must resolve for any website: a website-scoped "
                "stylesheet poisons every asset bundle compiled outside "
                "that website's context",
            )
