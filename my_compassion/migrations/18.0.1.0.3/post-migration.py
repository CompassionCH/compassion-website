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


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env["website"].search([("name", "=", "MyCompassion")], limit=1)
    if not website:
        return
    menus = env["website.menu"].search(
        [
            ("website_id", "=", website.id),
            ("url", "in", ["/shop", "/jobs"]),
        ]
    )
    if menus:
        _logger.info(
            "removing %s leftover navbar menu(s) from MyCompassion: %s",
            len(menus),
            menus.mapped("url"),
        )
        menus.unlink()
