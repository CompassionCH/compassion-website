##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.9 of theme_compassion_2025.

Seed the newly-translatable ``website.privacy_policy_url`` field with the
real per-language policy page confirmed on the live compassion.ch production
site, for every website running this theme. The field already held the
French URL as a plain (untranslated) value; this adds the German and Italian
equivalents alongside it.
"""

from odoo import SUPERUSER_ID, api

# (lang, privacy policy url)
PRIVACY_URL_BY_LANG = [
    ("fr_CH", "https://compassion.ch/protection-des-donnees/"),
    ("de_DE", "https://compassion.ch/de/datenschutz/"),
    ("it_IT", "https://compassion.ch/it/privacy-e-termini/"),
]


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    theme = env["ir.module.module"].search(
        [("name", "=", "theme_compassion_2025")], limit=1
    )
    if not theme:
        return
    websites = env["website"].search([("theme_id", "=", theme.id)])
    for lang, url in PRIVACY_URL_BY_LANG:
        websites.with_context(lang=lang).write({"privacy_policy_url": url})
