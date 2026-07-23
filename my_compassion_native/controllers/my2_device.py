##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from psycopg2 import IntegrityError

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MyCompassionDeviceController(http.Controller):
    @http.route(
        "/my2/api/register_device",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def register_device_token(self, token=None, device_type=None, **kwargs):
        if not token or not device_type:
            return {"status": "error", "message": "Missing token or device_type"}

        user = request.env.user
        TokenModel = request.env["mycompassion.device.token"].sudo()

        existing_token = TokenModel.search([("token", "=", token)], limit=1)

        if existing_token:
            if existing_token.user_id.id != user.id:
                existing_token.write({"user_id": user.id})
        else:
            try:
                TokenModel.create(
                    {"user_id": user.id, "token": token, "device_type": device_type}
                )
                TokenModel.flush_model()

            except IntegrityError:
                _logger.info("Device token registration race condition handled.")

        request.session["mycompassion_device_token"] = token

        return {"status": "success"}

    @http.route(
        "/my2/api/unregister_device",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def unregister_device_token(self, token=None, **kwargs):
        if not token:
            return {"status": "error", "message": "Missing token"}

        user = request.env.user
        TokenModel = request.env["mycompassion.device.token"].sudo()

        existing_tokens = TokenModel.search(
            [("token", "=", token), ("user_id", "=", user.id)]
        )

        if existing_tokens:
            existing_tokens.unlink()

        if "mycompassion_device_token" in request.session:
            request.session.pop("mycompassion_device_token")

        return {"status": "success", "message": "Device unregistered successfully"}
