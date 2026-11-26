##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import TransactionCase, tagged

from odoo.addons.my_compassion.tools.translations import reapply_translations

DETAILS_FORM = "my_compassion.my2_new_sponsorship_details_form"
REFERENCE = f"model_terms:ir.ui.view,arch_db:{DETAILS_FORM}"


@tagged("post_install", "-at_install")
class TestReapplyTranslations(TransactionCase):
    """A corrected translation reaches a database that stores the old one,
    and nothing else that database stores is touched."""

    def setUp(self):
        super().setUp()
        self.env["res.lang"]._activate_lang("fr_CH")
        self.view = self.env.ref(DETAILS_FORM)
        # what a database upgraded from the old catalog holds: the wrong zip
        # label, and a label staff reworded by hand
        self.view.update_field_translations(
            "arch_db", {"fr_CH": {"Code": "Réf. Enfant", "Street": "Adresse postale"}}
        )

    def _fr_arch(self):
        return self.view.with_context(lang="fr_CH").arch_db

    def test_the_listed_term_takes_the_catalog_translation(self):
        self.assertIn("Réf. Enfant", self._fr_arch())
        count = reapply_translations(
            self.env, "my_compassion", {"fr_CH": [[REFERENCE, "Code"]]}
        )
        self.assertEqual(count, 1)
        self.assertIn("NPA", self._fr_arch())
        self.assertNotIn("Réf. Enfant", self._fr_arch())

    def test_a_term_not_listed_keeps_what_is_stored(self):
        reapply_translations(
            self.env, "my_compassion", {"fr_CH": [[REFERENCE, "Code"]]}
        )
        self.assertIn("Adresse postale", self._fr_arch())

    def test_another_language_is_left_alone(self):
        """Only the languages listed are read and written."""
        self.env["res.lang"]._activate_lang("de_DE")
        self.view.update_field_translations(
            "arch_db", {"de_DE": {"Code": "Kinder Ref."}}
        )
        reapply_translations(
            self.env, "my_compassion", {"fr_CH": [[REFERENCE, "Code"]]}
        )
        self.assertIn("Kinder Ref.", self.view.with_context(lang="de_DE").arch_db)

    def test_an_inactive_language_is_skipped(self):
        self.assertEqual(
            reapply_translations(
                self.env, "my_compassion", {"xx_XX": [[REFERENCE, "Code"]]}
            ),
            0,
        )
