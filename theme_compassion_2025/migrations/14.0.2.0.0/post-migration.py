##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, registry):
    """
    Makes sure to generate the stylesheet for colors, icons and pictograms integration.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Clear the cache before processing the CSS generation from Qweb
    env["ir.qweb"].clear_caches()
    env["ir.ui.view"].clear_caches()
    env["theme.ir.ui.view"].clear_caches()

    models_to_update = [
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ]

    _logger.info("Post-migration: Generating theme stylesheets...")

    try:
        for model_name in models_to_update:
            env[model_name]._generate_stylesheet()

        _logger.info("Post-migration: Stylesheet generation complete.")
    except:
        _logger.error(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )
        _logger.error(
            "!! MIGRATION ERROR: Template not found during stylesheet generation. !!"
        )
        _logger.error(
            "!! Please downgrade the module to version 14.0.1.0.0 first,          !!"
        )
        _logger.error(
            "!! then run this upgrade to 14.0.2.0.0 again.                        !!"
        )
        _logger.error(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )
        raise
