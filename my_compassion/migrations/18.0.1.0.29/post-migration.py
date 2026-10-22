##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.29 of my_compassion.

A company that sets no suggested donation amounts on a product reads the
company-less ir.default values. The data file setting them is noupdate, so
it only runs at install: loaded here for the existing databases.
"""

from openupgradelib import openupgrade

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    openupgrade.load_data(env, "my_compassion", "data/donation_amount_defaults.xml")
