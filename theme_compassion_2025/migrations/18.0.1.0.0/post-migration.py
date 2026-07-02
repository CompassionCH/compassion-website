##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
##############################################################################
"""Post-migration to 18.0.1.0.0 of theme_compassion_2025.

Three jobs on upgrade:

1. Rename ir.attachment URLs from /theme/compassion/*.scss to
   /theme_compassion_2025/dynamic/*.scss (module-scoped). Records have
   noupdate="1" in data/dynamic_stylesheets.xml so the normal reload won't
   update the URL field; we do it explicitly via SQL.

2. Invalidate registry ormcache + theme.ir.ui.view template cache, so the
   next bundle compile picks up the new arch_db.

3. Synchronous regeneration of the 3 stylesheet attachments.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # (1) URL rename for ir.attachment records (idempotent)
    rename_map = {
        "/theme/compassion/colors.scss": "/theme_compassion_2025/dynamic/colors.scss",
        "/theme/compassion/icons.scss": "/theme_compassion_2025/dynamic/icons.scss",
        "/theme/compassion/pictograms.scss": "/theme_compassion_2025/dynamic/pictograms.scss",  # noqa: E501
    }
    for old_url, new_url in rename_map.items():
        cr.execute(
            "UPDATE ir_attachment SET url = %s WHERE url = %s",
            (new_url, old_url),
        )

    # (2) Cache invalidation: registry ormcache + theme template cache
    env.registry.clear_cache()
    # theme.ir.ui.view caches template arch_db; invalidate so next render re-fetches
    env["theme.ir.ui.view"].invalidate_model()

    # (3) Synchronous regeneration of the 3 stylesheet attachments
    for model_name in (
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ):
        env[model_name].sudo()._generate_stylesheet()
