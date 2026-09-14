##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.8 of theme_compassion_2025.

Seed the new translatable ``website.footer_address``/``footer_phone`` fields
(T3410) for every website running this theme, with the real per-language
office contact info confirmed on the live compassion.ch production site:
French-speaking Switzerland is served from Yverdon-les-Bains, German- and
Italian-speaking Switzerland share the Bern office (with a slightly
different phone extension per language).
"""

from odoo import SUPERUSER_ID, api

# (lang, address, phone)
FOOTER_CONTACT_BY_LANG = [
    ("fr_CH", "Rue Galilée 3, 1400 Yverdon-les-Bains", "+41 (0)24 434 21 24"),
    ("de_DE", "Parkterrasse 10, 3012 Bern", "+41 (0)31 552 21 21"),
    ("it_IT", "Parkterrasse 10, 3012 Bern", "+41 (0)31 552 21 24"),
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
    for lang, address, phone in FOOTER_CONTACT_BY_LANG:
        websites.with_context(lang=lang).write(
            {"footer_address": address, "footer_phone": phone}
        )
