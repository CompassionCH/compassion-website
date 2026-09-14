##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.7 of theme_compassion_2025.

Re-activate ``website.option_header_brand_logo``. This stock Odoo view
replaces the header's empty brand placeholder (``#o_fake_navbar_brand``) with
the actual ``<img>`` logo; it ships ``active="True"`` but is stored
``active=False`` with no per-website override on this instance, so no website
(MyCompassion included) renders a logo at all. Nothing in this codebase
injects a logo through any other mechanism, so this is a straight restore of
the shipped default, not a per-website customization.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref("website.option_header_brand_logo", raise_if_not_found=False)
    if view and not view.active:
        view.active = True
