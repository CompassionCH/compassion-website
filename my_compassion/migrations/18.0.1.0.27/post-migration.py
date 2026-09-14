##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.27 of my_compassion.

Re-activate the MyCompassion website's copy-on-write override of
``website_sale.template_header_default`` (T3410). That view injects the
cart/gift link into the *desktop* header; the base view and the "Compassion
Suisse" website's own copy are active, but the MyCompassion website (id
``my_compassion.my2_website``) has its own copy-on-write record stuck
``active=False``, so the gift icon my2_header_menu.xml re-styles
(``custom_header_cart_link_redirect``) only ever renders on the *mobile*
header (``website_sale.template_header_mobile`` has no such override) and is
missing entirely on desktop.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env.ref("my_compassion.my2_website", raise_if_not_found=False)
    if not website:
        return
    view = (
        env["ir.ui.view"]
        .with_context(active_test=False)
        .search(
            [
                ("key", "=", "website_sale.template_header_default"),
                ("website_id", "=", website.id),
            ],
            limit=1,
        )
    )
    if view and not view.active:
        view.active = True
