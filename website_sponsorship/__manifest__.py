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
    "name": "Website - Sponsor a child form",
    "version": "14.0.1.0.0",
    "category": "Website",
    "author": "Compassion CH",
    "development_status": "Beta",
    "license": "AGPL-3",
    "website": "https://www.compassion.ch",
    "depends": [
        "crm_compassion",
        "partner_auto_match",
        "partner_search_fuzzy",
        "website_form",
    ],
    "data": [
        "data/form_data.xml",
        "data/children_snippet_data.xml",
        "security/ir.model.access.csv",
        "security/access_rules.xml",
        "templates/assets.xml",
        "templates/child_page.xml",
        "templates/children_page.xml",
        "templates/form_success_page.xml",
        "templates/sponsorship_form.xml",
        "templates/data_protection_page.xml",
        "views/contract_origin_view.xml",
        "views/data_protection_view.xml",
        "views/child_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
