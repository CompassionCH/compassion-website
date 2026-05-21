##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    device_token_ids = fields.One2many(
        "mycompassion.device.token", "user_id", string="Mobile Device Tokens"
    )

    def notify_mobile_app(self, title, body, data=None):
        if not self.device_token_ids:
            return False
        return self.device_token_ids._send_push_notification(title, body, data)

    def action_open_push_notification_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "my2.push.notification.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_user_id": self.id},
        }
