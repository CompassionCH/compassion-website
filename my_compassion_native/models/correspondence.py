##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, models


class Correspondence(models.Model):
    _inherit = "correspondence"

    def write(self, vals):
        b2s_unpublished = self.filtered(
            lambda c: c.direction == "Beneficiary To Supporter" and not c.is_published
        )
        result = super().write(vals)
        for letter in b2s_unpublished:
            if letter.is_published:
                letter._notify_new_letter()
        return result

    def _notify_new_letter(self):
        users = self.sponsorship_id.sudo().partner_id.user_ids
        if not users:
            return
        child = self.sponsorship_id.child_id
        child_name = child.preferred_name or child.name
        for user in users:
            user.notify_mobile_app(
                _("New letter from %s") % child_name,
                _("%s has written you a letter!") % child_name,
                {"url": self.website_url},
            )
