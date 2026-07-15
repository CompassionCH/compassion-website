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
    """The MyCompassion website is now flagged with is_my_compassion (the
    portal resolves /my2 routes and applies its theme through that flag, so a
    multi-company instance can run one portal website per country). The
    shipped record is noupdate, so flag it here for existing databases.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env.ref("my_compassion.my2_website", raise_if_not_found=False)
    if website and not website.is_my_compassion:
        website.is_my_compassion = True
        _logger.info("Flagged website %s as MyCompassion.", website.id)
