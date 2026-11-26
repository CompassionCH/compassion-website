##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""T3109: per-language company name in the footer copyright of Swiss websites."""

from odoo import SUPERUSER_ID, api

FOOTER_COMPANY_NAME_BY_LANG = [
    ("en_US", "Compassion Suisse"),
    ("fr_CH", "Compassion Suisse"),
    ("de_DE", "Compassion Schweiz"),
    ("it_IT", "Compassion Svizzera"),
]


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    theme = env["ir.module.module"].search(
        [("name", "=", "theme_compassion_2025")], limit=1
    )
    websites = env["website"].search(
        [
            ("theme_id", "=", theme.id),
            ("company_id.partner_id.country_id.code", "=", "CH"),
        ]
    )
    for lang, name in FOOTER_COMPANY_NAME_BY_LANG:
        if env["res.lang"]._lang_get(lang):
            websites.with_context(lang=lang).write({"footer_company_name": name})

    # -u doesn't overwrite existing view translations: set the new German term.
    if env["res.lang"]._lang_get("de_DE"):
        key = "theme_compassion_2025.footer_2025"
        new_term = {"de_DE": {"Policies": "Datenschutz"}}
        for view in env["theme.ir.ui.view"].search([("key", "=", key)]):
            view.update_field_translations("arch", new_term)
        views = env["ir.ui.view"].with_context(active_test=False)
        for view in views.search([("key", "=", key)]):
            view.update_field_translations("arch_db", new_term)
