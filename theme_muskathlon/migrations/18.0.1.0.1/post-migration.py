import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# data/presets.xml used <record model="ir.ui.view"> instead of <template>, so it
# deactivated the generic views for every website instead of the Muskathlon ones.
# Restore the two that Odoo 18 ships enabled; the theme post copy now disables
# them per website.
VIEWS_TO_RESTORE = [
    "website.option_header_brand_logo",
    "website.header_language_selector",
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xml_id in VIEWS_TO_RESTORE:
        view = env.ref(xml_id, raise_if_not_found=False)
        if view and not view.active and not view.website_id:
            view.active = True
            _logger.info("Restored generic view %s", xml_id)
