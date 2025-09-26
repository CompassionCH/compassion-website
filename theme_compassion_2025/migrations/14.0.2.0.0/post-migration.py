import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, registry):
    """
    Makes sure to generate the stylesheet for colors, icons and pictograms integration.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    models_to_update = [
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ]

    _logger.info("Post-migration: Generating theme stylesheets...")

    for model_name in models_to_update:
        env[model_name]._generate_stylesheet()

    _logger.info("Post-migration: Stylesheet generation complete.")
