##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import datetime

from odoo import api, models


class CompassionChild(models.Model):
    _inherit = "compassion.child"

    @api.model
    def _cron_send_birthday_push_notifications(self):
        """Daily cron job to send push notifications for upcoming birthdays"""
        today = datetime.date.today()
        current_year = today.year

        children = self.search([("birthdate", "!=", False)])

        for child in children:
            try:
                next_bday = child.birthdate.replace(year=current_year)
            except ValueError:
                next_bday = child.birthdate.replace(year=current_year, month=3, day=1)

            if next_bday < today:
                try:
                    next_bday = next_bday.replace(year=current_year + 1)
                except ValueError:
                    next_bday = next_bday.replace(year=current_year + 1, month=3, day=1)

            days_until = (next_bday - today).days

            if 0 <= days_until <= 30:
                sponsorships = self.env["recurring.contract"].search(
                    [("child_id", "=", child.id), ("state", "=", "active")]
                )
                partners_to_notify = sponsorships.mapped(
                    "partner_id"
                ) | sponsorships.mapped("correspondent_id")

                for partner in partners_to_notify:
                    if not partner.user_ids:
                        continue
                    for user in partner.user_ids:
                        marker_subject = f"SYSTEM_PUSH_BDAY_{child.id}_{next_bday.year}"
                        already_sent = self.env["partner.log.other.interaction"].search(
                            [
                                ("partner_id", "=", partner.id),
                                ("subject", "=", marker_subject),
                            ],
                            limit=1,
                        )
                        if not already_sent:
                            tokens = self.env["mycompassion.device.token"].search(
                                [("user_id", "=", user.id)]
                            )
                            if tokens:
                                for token in tokens:
                                    token._send_push_notification(
                                        title="Upcoming Birthday!",
                                        body=f"{child.preferred_name}'s birthday"
                                        f" is coming up in {days_until} days!",
                                        data={"url": f"/my2/children/{child.id}"},
                                    )
                                self.env["partner.log.other.interaction"].create(
                                    {
                                        "partner_id": partner.id,
                                        "subject": marker_subject,
                                        "body": f"<p>Sent automated Push "
                                        f"Notification to device for "
                                        f"{child.preferred_name}'s "
                                        f"birthday.</p>",
                                        "communication_type": "Other",
                                        "other_type": "Push Notification",
                                        "direction": "out",
                                    }
                                )
