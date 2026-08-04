##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import datetime
from collections import defaultdict

from odoo import api, models

NOTIFICATION_HORIZON = 30


class CompassionChild(models.Model):
    _inherit = "compassion.child"

    @api.model
    def _cron_send_birthday_push_notifications(self):
        """Daily cron job to send push notifications for upcoming birthdays.

        Driven from the device tokens, not from the children: only users with a
        registered device can be notified.
        """
        tokens = self.env["mycompassion.device.token"].search(
            [("user_id.active", "=", True)]
        )
        if not tokens:
            return

        token_ids_by_user = defaultdict(list)
        for token in tokens:
            token_ids_by_user[token.user_id.id].append(token.id)

        user_ids_by_partner = defaultdict(list)
        for user in tokens.mapped("user_id"):
            user_ids_by_partner[user.partner_id.id].append(user.id)

        partner_ids = list(user_ids_by_partner)
        sponsorships = self.env["recurring.contract"].search(
            [
                ("state", "=", "active"),
                "|",
                ("partner_id", "in", partner_ids),
                ("correspondent_id", "in", partner_ids),
            ]
        )

        today = datetime.date.today()
        # (partner_id, child_id) -> (child, next_birthday, days_until)
        targets = {}
        for sponsorship in sponsorships:
            child = sponsorship.child_id
            if not child.birthdate:
                continue
            next_bday = self._next_birthday(child.birthdate, today)
            days_until = (next_bday - today).days
            if days_until > NOTIFICATION_HORIZON:
                continue
            for partner in sponsorship.partner_id | sponsorship.correspondent_id:
                if partner.id in user_ids_by_partner:
                    targets[(partner.id, child.id)] = (child, next_bday, days_until)

        if not targets:
            return

        markers = {
            key: f"SYSTEM_PUSH_BDAY_{child.id}_{next_bday.year}"
            for key, (child, next_bday, _days) in targets.items()
        }
        interactions = self.env["partner.log.other.interaction"]
        already_sent = {
            (log["partner_id"][0], log["subject"])
            for log in interactions.search_read(
                [
                    ("partner_id", "in", [partner_id for partner_id, _cid in targets]),
                    ("subject", "in", list(set(markers.values()))),
                ],
                ["partner_id", "subject"],
            )
        }

        logs = []
        for key, (child, _next_bday, days_until) in targets.items():
            partner_id = key[0]
            marker = markers[key]
            if (partner_id, marker) in already_sent:
                continue
            for user_id in user_ids_by_partner[partner_id]:
                devices = tokens.browse(token_ids_by_user[user_id])
                if devices._send_push_notification(
                    title="Upcoming Birthday!",
                    body=f"{child.preferred_name}'s birthday"
                    f" is coming up in {days_until} days!",
                    data={"url": f"/my2/children/{child.id}"},
                ):
                    logs.append(
                        {
                            "partner_id": partner_id,
                            "subject": marker,
                            "body": f"<p>Sent automated Push Notification to "
                            f"device for {child.preferred_name}'s birthday.</p>",
                            "communication_type": "Other",
                            "other_type": "Push Notification",
                            "direction": "out",
                        }
                    )
                    already_sent.add((partner_id, marker))
                    break

        if logs:
            interactions.create(logs)

    @staticmethod
    def _next_birthday(birthdate, today):
        def anniversary(year):
            try:
                return birthdate.replace(year=year)
            except ValueError:
                # 29 February in a non-leap year
                return datetime.date(year, 3, 1)

        this_year = anniversary(today.year)
        return this_year if this_year >= today else anniversary(today.year + 1)
