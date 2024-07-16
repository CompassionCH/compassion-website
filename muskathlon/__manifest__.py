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
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Sebastien Toth <popod@me.com>
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# pylint: disable=C8101
{
    "name": "Muskathlon",
    "version": "14.0.1.2.0",
    "category": "Reports",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "maintainers": ["ecino"],
    "development_status": "Production/Stable",
    "data": [
        "security/ir.model.access.csv",
        "security/access_rules.xml",
        "data/default_sports.xml",
        "data/form_data.xml",
        "data/res_users.xml",
        "data/survey_muskathlon_medical_infos.xml",
        "data/product.xml",
        "data/mail_template.xml",
        "data/event_registration_stage.xml",
        "data/event_type.xml",
        "data/event_registration_task.xml",
        "data/event_type_mail.xml",
        "data/order_material_mail_template.xml",
        "data/queue_job.xml",
        "data/website.xml",
        "reports/muskathlon_view.xml",
        "views/event_compassion_view.xml",
        "views/recurring_contracts_view.xml",
        "views/muskathlon_registrations.xml",
        "views/notification_settings_view.xml",
        "templates/muskathlon_page.xml",
        "templates/muskathlon_registration_form.xml",
        "templates/muskathlon_order_material.xml",
        "templates/my_tasks_forms.xml",
        "templates/donation_result.xml",
        "templates/assets.xml",
        "templates/muskathlon_address_form.xml",
        "data/website_redirect.xml",
    ],
    "depends": [
        "website_event_compassion",
    ],
    "external_dependencies": {},
    "demo": [],
    "installable": True,
    "auto_install": False,
}
