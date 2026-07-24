##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
##############################################################################
"""Post-migration to 18.0.1.0.5 of theme_compassion_2025.

The icon and pictogram stylesheet templates gained -webkit-mask-* prefixes so
the masked SVG icons render on Safari and older Chromium. The dynamic
stylesheet attachments are noupdate and an upgrade does not run the install
hook, so regenerate them here to serve the new CSS. The regeneration also
clears the assets cache so the new bundle goes live.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    for model_name in (
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ):
        env[model_name].sudo()._generate_stylesheet()
