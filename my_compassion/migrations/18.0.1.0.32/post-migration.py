##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.32 of my_compassion.

recurring.contract.my2_details_awaited_partner names the partner a fast
checkout created, and the details form only ever opens on that partner. The
signups still waiting for their sponsor's name get it here, from the partner
that still carries the placeholder: the only partner a fast checkout ever
gives one.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE recurring_contract contract
        SET my2_details_awaited_partner = contract.partner_id
        FROM res_partner partner
        WHERE partner.id = contract.partner_id
            AND contract.my2_signup
            AND partner.my2_name_placeholder
            AND COALESCE(contract.my2_details_awaited_partner, 0) = 0
        """
    )
