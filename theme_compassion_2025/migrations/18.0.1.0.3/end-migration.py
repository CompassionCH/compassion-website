##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
##############################################################################
"""End-migration to 18.0.1.0.3 of theme_compassion_2025.

Apply the website "Page Layout: Full" option to the websites using this theme,
so the cutover upgrade reproduces the setting the editor would write. The shared
implementation and rationale live in ``hooks._set_full_page_layout``.

This runs at the ``end`` stage, not ``post``: ``make_scss_customization``
recomputes the ``web.assets_frontend`` bundle, which references this theme's own
assets, and a module is only present in ``registry._init_modules`` (the
installed-addons list that bundle computation checks) from the end stage onward.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.theme_compassion_2025.hooks import _set_full_page_layout


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_full_page_layout(env)
    env.registry.clear_cache()
