##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.8 of theme_compassion_2025.

Seed the translatable ``website.footer_address``/``footer_phone`` fields of
the Swiss websites running this theme (company partner in Switzerland) with
the per-language office contact info of compassion.ch: French-speaking
Switzerland is served from Yverdon-les-Bains, German- and Italian-speaking
Switzerland share the Bern office (with a slightly different phone extension
per language). Only the languages active on the database are written, and
websites of other countries are left untouched.
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
    # res.company.country_id is a non-stored compute: search on the partner's.
    websites = env["website"].search(
        [
            ("theme_id", "=", theme.id),
            ("company_id.partner_id.country_id.code", "=", "CH"),
        ]
    )
    # A write with an inactive language in context raises a UserError.
    for lang, address, phone in FOOTER_CONTACT_BY_LANG:
        if env["res.lang"]._lang_get(lang):
            websites.with_context(lang=lang).write(
                {"footer_address": address, "footer_phone": phone}
            )
