##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
##############################################################################
"""Post-migration to 18.0.1.0.2 of theme_compassion_2025.

Re-parent the Compassion theme module category under the canonical
``base.module_category_theme``.

``website.get_themes_domain()`` only recognises a module as a theme when its
category is ``base.module_category_theme`` or a direct child of it. The
Compassion themes share a "Compassion" category whose parent is a duplicate
"Theme" category, so they are not recognised as themes. As a consequence
``ir.asset._get_active_addons_list()`` cannot discard the inactive themes when
building a website's assets, and every installed theme ships its global
``primary_variables`` (and palette) into every website's bundle.

It also restores generated/loaded state that a plain upgrade drops:
- the brand stylesheet attachments are regenerated (an upgrade does not run the
  install hook, so they come back empty and the website renders unstyled);
- missing icon/pictogram ``svg_file`` binaries are reloaded from the module's
  static sources. The icon data is ``noupdate``, so an upgrade never reloads it;
  a DB restored without its matching filestore then keeps the rows while their
  files are gone, and every ``/web/image/.../svg_file`` mask resolves to nothing
  (icons render invisible).
"""

import base64
import logging
import os

from odoo import api, SUPERUSER_ID
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

THEME_MODULES = [
    "theme_compassion",
    "theme_compassion_2025",
    "theme_crowdfunding",
    "theme_muskathlon",
]

# The records load svg_file from these directories at install (data is noupdate),
# keyed by record name: a record named "Activity" maps to "Activity.svg".
SVG_SOURCES = {
    "theme.compassion.icons": "theme_compassion_2025/static/src/img/icons",
    "theme.compassion.pictograms": "theme_compassion_2025/static/src/img/pictograms",
}


def _heal_missing_svg_binaries(env):
    """Reload icon/pictogram svg_file binaries whose filestore file is gone.

    No-op when the files are present (a clean install loads them natively). The
    backing ir.attachment is written directly so the model's per-record
    stylesheet-regeneration override does not fire once per record.
    """
    attachments = env["ir.attachment"]
    healed = 0
    for model_name, static_dir in SVG_SOURCES.items():
        records = env[model_name].search([])
        attachment_by_record = {
            attachment.res_id: attachment
            for attachment in attachments.search(
                [
                    ("res_model", "=", model_name),
                    ("res_field", "=", "svg_file"),
                    ("res_id", "in", records.ids),
                ]
            )
        }
        for record in records:
            attachment = attachment_by_record.get(record.id)
            if (
                attachment
                and attachment.store_fname
                and os.path.exists(attachment._full_path(attachment.store_fname))
            ):
                continue
            try:
                with file_open(f"{static_dir}/{record.name}.svg", "rb") as svg:
                    data = svg.read()
            except (FileNotFoundError, OSError):
                _logger.warning(
                    "%s '%s' has no static source SVG; cannot restore its file.",
                    model_name,
                    record.name,
                )
                continue
            if attachment:
                attachment.write({"raw": data, "mimetype": "image/svg+xml"})
            else:
                record.svg_file = base64.b64encode(data)
            healed += 1
    if healed:
        _logger.info("Restored %s missing theme SVG binaries.", healed)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    theme_category = env.ref("base.module_category_theme", raise_if_not_found=False)
    if theme_category:
        themes = env["ir.module.module"].search([("name", "in", THEME_MODULES)])
        for category in themes.category_id:
            if category != theme_category and category.parent_id != theme_category:
                category.parent_id = theme_category

    _heal_missing_svg_binaries(env)

    for model_name in (
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ):
        env[model_name].sudo()._generate_stylesheet()
