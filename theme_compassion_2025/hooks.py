def _post_init_hook(cr, registry):
    """
    This hook is called after the module is installed.
    His purpose is to call the generation of the needed
    attachment generated stylesheets.
    """
    import logging

    from odoo import SUPERUSER_ID, api

    _logger = logging.getLogger(__name__)

    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Post-init hook: Generating theme stylesheets.")

    models_to_process = [
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ]

    for model_name in models_to_process:
        env[model_name]._generate_stylesheet()

    _logger.info("Post-init hook: Stylesheet generation complete.")
