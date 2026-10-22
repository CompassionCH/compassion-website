##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.29 of my_compassion.

The partners a visitor creates from an email they typed are flagged
my2_email_unverified at creation, so that signup never links an account to
them. The fast checkout created such partners before the flag existed: those
still known by the placeholder name and without an account are flagged here.
A partner named since then cannot be told apart from any other.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_partner partner
        SET my2_email_unverified = TRUE
        WHERE partner.my2_name_placeholder
            AND NOT COALESCE(partner.my2_email_unverified, FALSE)
            AND NOT EXISTS (
                SELECT 1 FROM res_users WHERE res_users.partner_id = partner.id
            )
        """
    )
