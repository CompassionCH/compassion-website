##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tools import parse_version


def migrate(cr, version):
    """This version needs payment_payu_gpo with the first and last names on
    the card, upgraded with it: without it, the post-processing of every
    online payment fails, and an old card form (one name input) makes every
    PayU card payment refused.

    The version is checked, not the column: upgrading my_compassion creates
    the columns of the models it extends without upgrading payment_payu_gpo.
    payment_payu_gpo, a dependency, is loaded and its version saved before
    this pre-migration runs.
    """
    cr.execute(
        "SELECT latest_version FROM ir_module_module WHERE name = 'payment_payu_gpo'"
    )
    row = cr.fetchone()
    if not row or parse_version(row[0] or "0") < parse_version("18.0.1.1.0"):
        raise RuntimeError(
            "Upgrade payment_payu_gpo 18.0.1.1.0"
            " (CompassionCH/compassion-accounting#298) together with this module:"
            " -u payment_payu_gpo,my_compassion_payment_payu_gpo"
        )
