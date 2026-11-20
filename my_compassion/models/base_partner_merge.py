##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models

# Flags about how a partner came to be, which only the partner itself can
# vouch for: a merge never hands them from one contact to another.
MY2_OWN_FLAGS = (
    "my2_email_unverified",
    "my2_name_placeholder",
    "my2_duplicate_flagged",
)


class MergePartnerAutomatic(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _update_values(self, src_partners, dst_partner):
        """The standard merge copies a value from a removed contact when the
        kept one has it empty, and a False boolean counts as empty. Merging a
        visitor's contact into a donor would then make the donor read as
        unverified (no account linking any more) or as still nameless."""
        own_flags = {flag: dst_partner[flag] for flag in MY2_OWN_FLAGS}
        res = super()._update_values(src_partners, dst_partner)
        if any(dst_partner[flag] != value for flag, value in own_flags.items()):
            dst_partner.write(own_flags)
        return res
