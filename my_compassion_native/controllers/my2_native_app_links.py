##############################################################################
#
#    Copyright (C) 2020-2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json

from odoo import http
from odoo.http import request


class UniversalLinks(http.Controller):
    # Apple App Site Association (iOS)
    @http.route(
        "/.well-known/apple-app-site-association",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def apple_app_site_association(self, **kwargs):
        data = {
            "applinks": {
                "apps": [],
                "details": [
                    {"appID": "33XBVM48T4.ch.mycompassion.app", "paths": ["*"]}
                ],
            }
        }
        # Apple strictly requires the content type to be application/json
        return request.make_response(
            json.dumps(data), headers=[("Content-Type", "application/json")]
        )

    # Android Asset Links (Android)
    @http.route(
        "/.well-known/assetlinks.json",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def android_asset_links(self, **kwargs):
        data = [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": "ch.mycompassion.app",
                    "sha256_cert_fingerprints": ["YOUR_ANDROID_SHA256_FINGERPRINT"],
                },
            }
        ]
        return request.make_response(
            json.dumps(data), headers=[("Content-Type", "application/json")]
        )
