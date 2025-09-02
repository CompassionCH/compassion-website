def _post_init_hook(cr, registry):
    """
    This hook is called after the module is installed.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Generate the stylesheets for each model
    env["theme.compassion.colors"]._generate_stylesheet()
    env["theme.compassion.icons"]._generate_stylesheet()
    env["theme.compassion.pictograms"]._generate_stylesheet()
