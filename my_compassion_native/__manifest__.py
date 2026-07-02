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
    "version": "14.0.1.0.0",
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
        "templates/native_assets.xml",
    ],
    "depends": [
        "my_compassion",
    ],
    "demo": [],
    "installable": False,
    "auto_install": False,
}
