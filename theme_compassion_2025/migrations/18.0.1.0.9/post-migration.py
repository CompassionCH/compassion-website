##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.9 of theme_compassion_2025.

Seed the translatable ``website.privacy_policy_url`` field of the Swiss
websites running this theme (company partner in Switzerland) with the
per-language policy page of compassion.ch, in French, German and Italian.
Only the languages active on the database are written, and websites of other
countries are left untouched.
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
    # res.company.country_id is a non-stored compute: search on the partner's.
    websites = env["website"].search(
        [
            ("theme_id", "=", theme.id),
            ("company_id.partner_id.country_id.code", "=", "CH"),
        ]
    )
    # A write with an inactive language in context raises a UserError.
    for lang, url in PRIVACY_URL_BY_LANG:
        if env["res.lang"]._lang_get(lang):
            websites.with_context(lang=lang).write({"privacy_policy_url": url})
