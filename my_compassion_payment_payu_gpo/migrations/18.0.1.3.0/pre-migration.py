##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################


def migrate(cr, version):
    """This version reads the first and last names on the card of every
    confirmed payment, of all providers: without them, the post-processing of
    every online payment would fail. payment_payu_gpo is loaded before this
    module, which depends on it."""
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name ="
        " 'payment_transaction' AND column_name = 'payu_gpo_cardholder_firstname'"
    )
    if not cr.fetchone():
        raise RuntimeError(
            "payment_payu_gpo with the first and last names on the card"
            " (compassion-accounting#298) must be deployed with this version."
        )
