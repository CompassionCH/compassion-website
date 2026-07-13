##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

DYNAMIC_STYLESHEET_XMLIDS = [
    "theme_compassion_2025.theme_compassion_stylesheet_colors",
    "theme_compassion_2025.theme_compassion_stylesheet_pictograms",
    "theme_compassion_2025.theme_compassion_stylesheet_icons",
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _unscope_dynamic_stylesheets(env)
    from odoo.addons.my_compassion.hooks import _apply_my2_theme

    _apply_my2_theme(env)


def _unscope_dynamic_stylesheets(env):
    """The dynamic stylesheet attachments must stay global: an asset bundle
    compiled outside the MyCompassion website context cannot resolve a
    website-scoped attachment (empty lookup), which poisons the bundle cache.
    Per-website inclusion is already handled by the theme's asset records.
    """
    for xmlid in DYNAMIC_STYLESHEET_XMLIDS:
        attachment = env.ref(xmlid, raise_if_not_found=False)
        if attachment and attachment.website_id:
            attachment.website_id = False
            _logger.info("Unscoped dynamic stylesheet %s.", xmlid)
