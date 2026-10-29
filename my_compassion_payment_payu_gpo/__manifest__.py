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
    "version": "18.0.1.0.0",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "depends": ["my_compassion", "payment_payu_gpo"],
    "installable": True,
    "auto_install": True,
}
