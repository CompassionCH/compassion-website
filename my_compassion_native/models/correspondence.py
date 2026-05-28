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

    def process_letter(self):
        result = super().process_letter()
        self._notify_new_letter()
        return result

    def _notify_new_letter(self):
        partner = self.sponsorship_id.sudo().partner_id
        users = partner.user_ids
        if not users:
            return

        marker_subject = f"SYSTEM_PUSH_LETTER_{self.id}"
        already_sent = self.env["partner.log.other.interaction"].search(
            [("partner_id", "=", partner.id), ("subject", "=", marker_subject)],
            limit=1,
        )
        if already_sent:
            return

        child = self.sponsorship_id.child_id
        child_name = child.preferred_name or child.name
        success = False
        for user in users:
            if user.notify_mobile_app(
                _("New letter from %s") % child_name,
                _("%s has written you a letter!") % child_name,
                {"url": self.website_url},
            ):
                success = True

        if success:
            self.env["partner.log.other.interaction"].create(
                {
                    "partner_id": partner.id,
                    "subject": marker_subject,
                    "body": f"<p>Sent Push Notification for new letter"
                    f" from {child_name}.</p>",
                    "communication_type": "Other",
                    "other_type": "Push Notification",
                    "direction": "out",
                }
            )
