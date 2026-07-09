##############################################################################
#
#       ______ Releasing children from poverty      _
#      / ____/___  ____ ___  ____  ____ ___________(_)___  ____
#     / /   / __ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ / __ \/ __ \
#    / /___/ /_/ / / / / / / /_/ / /_/ (__  |__  ) / /_/ / / / /
#    \____/\____/_/ /_/ /_/ .___/\__,_/____/____/_/\____/_/ /_/
#                        /_/
#                            in Jesus' name
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Compassion Events Website",
    "summary": "Public website pages for Compassion Events with registration",
    "version": "18.0.1.0.0",
    "development_status": "Production/Stable",
    "category": "Marketing/Events",
    "website": "https://github.com/CompassionCH/compassion-website",
    "author": "Compassion Switzerland",
    "maintainers": ["ecino"],
    "license": "AGPL-3",
    "depends": [
        "crm_compassion",  # compassion-modules
        "child_protection",
        "event_sale",
        "website_sale_donation",
        "survey",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/access_rules.xml",
        "data/event_registration_stage.xml",
        "data/base_automation.xml",
        "data/event_message_subtype.xml",
        "data/event_type.xml",
        "data/form_data.xml",
        "data/product_template.xml",
        "views/event_compassion_open_wizard.xml",
        "views/event_compassion_view.xml",
        "views/event_event_view.xml",
        "views/event_registration_view.xml",
        "views/registration_stage_view.xml",
        "views/registration_task_view.xml",
        "views/event_type_view.xml",
        "views/event_registration_communication_wizard.xml",
        "templates/event_page.xml",
        "templates/events_list.xml",
        "templates/event_registration.xml",
        "templates/participants_list.xml",
        "templates/participant_page.xml",
        "templates/event_donation.xml",
        "templates/event_donation_result.xml",
        "templates/my_events.xml",
        "templates/website_cart.xml",
        "data/website_page.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_event_compassion/static/src/js/registration_form_page.esm.js",
            "website_event_compassion/static/src/js/donation_form.esm.js",
        ],
        "website.assets_wysiwyg": [
            "website_event_compassion/static/src/js/registration_form_snippet.esm.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
