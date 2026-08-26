##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# pylint: disable=C8101
{
    "name": "MyCompassion - Native App",
    "version": "18.0.1.0.1",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "external_dependencies": {"python": ["firebase-admin"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_push_notifications_cron.xml",
        "views/capacitor_content_load_fix.xml",
        "views/capacitor_viewport_fix.xml",
        "views/my2_push_notification_wizard_view.xml",
        "views/my2_bottom_nav.xml",
        "views/my2_mobile_profile.xml",
        "views/res_config_settings_view.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "my_compassion_native/static/src/scss/native_app.scss",
            "my_compassion_native/static/src/js/capacitor_bridge.js",
            "my_compassion_native/static/src/js/capacitor_pdf_util.js",
            "my_compassion_native/static/src/js/capacitor_push.js",
            "my_compassion_native/static/src/js/capacitor_ui_fix.js",
            "my_compassion_native/static/src/js/native_pdf_intercept.js",
            "my_compassion_native/static/src/js/payment_resume.js",
            "my_compassion_native/static/src/scss/payment_banner.scss",
        ],
    },
    "depends": [
        "my_compassion",
        # models/ use partner.log.other.interaction (interaction_resume) and
        # override correspondence.process_letter (sbc_translation)
        "interaction_resume",
        "sbc_translation",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
