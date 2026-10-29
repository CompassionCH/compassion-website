##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class My2PushNotificationWizard(models.TransientModel):
    _name = "my2.push.notification.wizard"
    _description = "Send Manual Push Notification"

    user_id = fields.Many2one("res.users", string="User", required=True, readonly=True)
    title = fields.Char(string="Title", required=True)
    body = fields.Text(string="Message", required=True)
    url = fields.Char(
        string="Deep Link URL",
        help="Optional: navigate to this URL when the user taps the notification "
        "(e.g. /my/letters)",
    )

    def action_send(self):
        self.ensure_one()
        data = {"url": self.url} if self.url else {}
        report = self.user_id.notify_mobile_app_report(
            self.title, self.body, data or None
        )
        if not report:
            raise UserError(
                _("%s has no device registered for push notifications.")
                % self.user_id.name
            )

        failures = [line for line in report if not line["sent"]]
        if len(failures) == len(report):
            raise UserError(
                _("Failed to send the push notification:\n%s")
                % self._format_failures(failures)
            )

        self.env["partner.log.other.interaction"].create(
            {
                "partner_id": self.user_id.partner_id.id,
                "subject": self.title,
                "body": f"<p>{self.body}</p>",
                "communication_type": "Other",
                "other_type": "Push Notification",
                "direction": "out",
            }
        )
        sent = len(report) - len(failures)
        # Say which devices took it: reporting the set as a whole is what let a
        # notification that never arrived look like a success (T3480).
        message = _("Sent to %(sent)s of %(total)s registered devices.") % {
            "sent": sent,
            "total": len(report),
        }
        if failures:
            message += "\n" + self._format_failures(failures)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Notification sent"),
                "message": message,
                "type": "warning" if failures else "success",
                "sticky": bool(failures),
            },
        }

    @staticmethod
    def _format_failures(failures):
        return "\n".join(
            _("%(device)s: %(error)s")
            % {"device": line["device_type"], "error": line["error"]}
            for line in failures
        )
