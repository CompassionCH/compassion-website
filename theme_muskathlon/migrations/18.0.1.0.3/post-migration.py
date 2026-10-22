import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """The Muskathlon websites show no footer body, only the copyright bar.
    The post copy of the theme does it for the new websites only: the
    existing ones still showed the demo footer of Odoo."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    websites = env["website"].search([("theme_id.name", "=", "theme_muskathlon")])
    for website in websites:
        theme_utils = env["theme.utils"].with_context(website_id=website.id)
        for footer in theme_utils._footer_templates:
            theme_utils.disable_view(footer)
        theme_utils.disable_view("website.option_footer_scrolltop")
        _logger.info("Footer body removed from the website %s", website.name)
