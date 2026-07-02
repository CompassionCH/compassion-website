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

_logger = logging.getLogger(__name__)

USER_VALUES_URL = "/website/static/src/scss/options/user_values.scss"


def _set_full_page_layout(env):
    """Apply the website "Page Layout: Full" option to every website running
    this theme, the same way the editor's Page Layout option does.
    """
    theme = env["ir.module.module"].search(
        [("name", "=", "theme_compassion_2025")], limit=1
    )
    if not theme:
        return
    assets = env["web_editor.assets"]
    websites = env["website"].search([("theme_id", "=", theme.id)])
    for website in websites:
        assets.with_context(website_id=website.id).make_scss_customization(
            USER_VALUES_URL, {"layout": "'full'"}
        )
    if websites:
        _logger.info("Applied full page layout to websites %s.", websites.ids)


def _post_init_hook(env):
    """Called after the module is installed to generate the colors, icons and
    pictograms stylesheet attachments from their records, and to set the
    full-width page layout on the websites using this theme.
    """
    for model_name in (
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ):
        env[model_name].sudo()._generate_stylesheet()
    _set_full_page_layout(env)
