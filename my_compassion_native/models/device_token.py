##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json
import logging

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin import exceptions as fb_exceptions

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MyCompassionDeviceToken(models.Model):
    """Model to store user mobile device tokens for push notifications"""

    _name = "mycompassion.device.token"
    _description = "User Device Tokens for Push Notifications"

    user_id = fields.Many2one(
        "res.users", string="User", required=True, ondelete="cascade"
    )
    token = fields.Char(string="Device Token", required=True, index=True)
    device_type = fields.Selection(
        [("ios", "iOS"), ("android", "Android")], string="Device Type", required=True
    )

    _sql_constraints = [("token_uniq", "unique(token)", "This token already exists!")]

    def _get_firebase_app(self):
        """
        Initializes and returns an ISOLATED Firebase App
        to prevent module conflicts
        """
        app_name = "my_compassion_native"
        try:
            # Try to get OUR specific named app, ignoring the default one
            return firebase_admin.get_app(name=app_name)
        except ValueError:
            # Fetch config from System Parameters
            json_config_str = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("my_compassion.fcm_service_account")
            )
            if not json_config_str:
                _logger.error(
                    "FCM Service Account JSON not found in System Parameters."
                )
                return None

            try:
                service_account_info = json.loads(json_config_str)
                # Keep newline fix just as a safety net
                if "private_key" in service_account_info:
                    service_account_info["private_key"] = service_account_info[
                        "private_key"
                    ].replace("\\n", "\n")

                cred = credentials.Certificate(service_account_info)
                try:
                    return firebase_admin.initialize_app(cred, name=app_name)
                except ValueError:
                    # Another worker initialized the app concurrently
                    return firebase_admin.get_app(name=app_name)
            except Exception as e:
                _logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
                return None

    def _send_push_notification(self, title, body, data=None):
        """Internal method to send push via FCM HTTP v1 API"""
        app = self._get_firebase_app()
        if not app:
            _logger.error("Push Notification failed: Firebase app not initialized.")
            return False

        sanitized_data = {str(k): str(v) for k, v in (data or {}).items()}
        records_with_tokens = self.filtered("token")

        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=sanitized_data,
                token=record.token,
            )
            for record in records_with_tokens
        ]

        if not messages:
            return False

        batch_response = messaging.send_each(messages, app=app)

        success_count = 0
        for record, response in zip(records_with_tokens, batch_response.responses):
            if response.success:
                _logger.info(
                    f"[Firebase] Successfully sent message to "
                    f"{record.user_id.login}: {response.message_id}"
                )
                success_count += 1
            elif isinstance(response.exception, fb_exceptions.NotFoundError):
                _logger.warning(
                    f"[Firebase] Token no longer valid for"
                    f" {record.user_id.login}, removing."
                )
                record.sudo().unlink()
            else:
                _logger.error(
                    f"[Firebase] Failed to send push to token {record.token}:"
                    f" {response.exception}"
                )

        return success_count > 0
