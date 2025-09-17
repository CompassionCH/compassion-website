def _post_init_hook(cr, registry):
    """
    This hook is called after the module is installed.
    """
    import logging

    from odoo import SUPERUSER_ID, api

    _logger = logging.getLogger(__name__)

    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Generating theme stylesheets via post-init hook...")

    # Generate the stylesheets for each model
    env["theme.compassion.colors"]._generate_stylesheet()
    env["theme.compassion.icons"]._generate_stylesheet()
    env["theme.compassion.pictograms"]._generate_stylesheet()

    _logger.info("Theme stylesheet generation complete.")
