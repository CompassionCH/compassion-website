##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
# pylint: disable=C8101
{
    "name": "Website - Compassion Switzerland custom views",
    "version": "14.0.1.0.0",
    "category": "Website",
    "author": "Compassion Switzerland",
    "development_status": "Beta",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "depends": [
        "my_compassion_segmentation",
        "theme_compassion",
        "partner_communication_switzerland",
        "website_crm_request",
    ],
    "data": [
        "data/res_lang.xml",
        "data/website_rewrite.xml",
        "templates/footer.xml",
        "templates/contact_us.xml",
    ],
    "installable": True,
    "auto_install": False,
}
