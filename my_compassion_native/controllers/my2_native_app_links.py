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

# Short links redirect to other sites, so they must open in the browser (T3660).
SHORT_LINK_COMPONENTS = [{"/": "/r/*", "exclude": True}, {"/": "*"}]


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
        get_param = request.env["ir.config_parameter"].sudo().get_param
        ios_app_id = get_param("my_compassion_native.ios_app_id", "")
        data = {
            "applinks": {
                "apps": [],
                "details": [
                    {
                        # iOS 13+ reads only appIDs/components; older iOS reads paths.
                        "appIDs": [ios_app_id],
                        "components": SHORT_LINK_COMPONENTS,
                        "appID": ios_app_id,
                        "paths": ["NOT /r/*", "*"],
                    }
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
        get_param = request.env["ir.config_parameter"].sudo().get_param
        fingerprint = get_param("my_compassion_native.android_sha256_fingerprint", "")
        package_name = get_param("my_compassion_native.android_package_name", "")
        data = [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                # Android 15+ only; older versions still open short links in the app.
                "relation_extensions": {
                    "delegate_permission/common.handle_all_urls": {
                        "dynamic_app_link_components": SHORT_LINK_COMPONENTS
                    }
                },
                "target": {
                    "namespace": "android_app",
                    "package_name": package_name,
                    "sha256_cert_fingerprints": [fingerprint],
                },
            }
        ]
        return request.make_response(
            json.dumps(data), headers=[("Content-Type", "application/json")]
        )
