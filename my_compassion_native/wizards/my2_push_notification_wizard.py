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
        success = self.user_id.notify_mobile_app(self.title, self.body, data or None)
        if not success:
            raise UserError(
                _(
                    "Failed to send the push notification. "
                    "Check that the user has registered devices and that "
                    "Firebase is configured correctly."
                )
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Notification sent"),
                "message": _("Push notification successfully sent to %s.")
                % self.user_id.name,
                "type": "success",
                "sticky": False,
            },
        }
