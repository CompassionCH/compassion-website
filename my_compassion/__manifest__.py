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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# pylint: disable=C8101
{
    "name": "MyCompassion - Sponsor portal website",
    "version": "14.0.1.0.0",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "data": [
        "security/access_rules.xml",
        "security/ir.model.access.csv",
        "templates/my_account_components.xml",
        "templates/my_account_personal_info.xml",
        "templates/my_account_donations.xml",
        "templates/my_account_my_children.xml",
        "templates/my_account_write_a_letter.xml",
        "templates/login_template.xml",
        "templates/signup.xml",
        "views/correspondence_template_view.xml",
        "views/partner_compassion_view.xml",
    ],
    "depends": [
        "partner_communication_compassion",
        "wordpress_configuration",
        "website_child_protection",
        "website_sponsorship",
        "auth_signup",
        "website_crm_privacy_policy",  # OCA/website
    ],
    "demo": [],
    "installable": True,
    "auto_install": False
}
