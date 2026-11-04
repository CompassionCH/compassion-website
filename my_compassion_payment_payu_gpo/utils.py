##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################


def normalize_cardholder_name(name):
    """The name on the card as PayU's card form cleans it: whitespace
    collapsed, 100 characters at most."""
    return " ".join(str(name or "").split())[:100]
