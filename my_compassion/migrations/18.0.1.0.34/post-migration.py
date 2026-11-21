##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Give the MyCompassion websites created besides the first one (e.g.
    Poland) its login, signup and consent views."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.my_compassion.hooks import _configure_my2_websites

    _configure_my2_websites(env)
