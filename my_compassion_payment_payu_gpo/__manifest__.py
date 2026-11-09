##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################

# pylint: disable=C8101
{
    "name": "MyCompassion - PayU GPO",
    "summary": "Sponsorship cards paid with PayU are saved as recurring cards",
    "version": "18.0.1.3.0",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "depends": ["my_compassion", "payment_payu_gpo"],
    "data": [
        "views/my2_gift_package.xml",
        "views/my2_new_sponsorship_wizard.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "my_compassion_payment_payu_gpo/static/src/js/*.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
