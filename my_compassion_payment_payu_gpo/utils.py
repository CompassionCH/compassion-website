##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request

from odoo.addons.payment import utils as payment_utils


def normalize_cardholder_name(name):
    """A name on the card as PayU's card form cleans it: whitespace
    collapsed, 100 characters at most."""
    return " ".join(str(name or "").split())[:100]


def session_cardholder_names(key):
    """The first and last names on the card kept in the session under key,
    as {record id: [firstname, lastname]}.

    A session from before the names were asked apart holds the full name,
    split as the card form of PayU then did.
    """
    names = {}
    for record_id, value in (request.session.get(key) or {}).items():
        if isinstance(value, str):
            value = payment_utils.split_partner_name(value) if value.strip() else ()
        if isinstance(value, list | tuple) and len(value) == 2:
            names[record_id] = list(value)
    return names
