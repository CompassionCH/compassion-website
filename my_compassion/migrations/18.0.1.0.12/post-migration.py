##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Enforce the portal website state (stock menus removed, stock
    footer/header option views archived) on databases installed before the
    state was applied by code.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.my_compassion.hooks import _configure_my2_websites

    _configure_my2_websites(env)
