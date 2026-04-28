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
#    @author: Noé Berdoz <nberdoz@compassion.ch>
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
    "version": "14.0.1.0.3",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "data": [
        "security/access_rules.xml",
        "security/ir.model.access.csv",
        # My Compassion 2 data
        "data/my2_website.xml",
        "data/my2_website_redirect.xml",
        "data/auto_letter_templates_updater_cron.xml",
        # My compassion 2 assets, needs to be placed before others
        "templates/my2_assets.xml",
        "templates/my_account_components.xml",
        "templates/my_account_personal_info.xml",
        "templates/my_account_donations.xml",
        "templates/my_account_my_children.xml",
        "templates/my_account_write_a_letter.xml",
        "templates/login_template.xml",
        "templates/signup.xml",
        "templates/my2_change_password.xml",
        "views/correspondence_template_view.xml",
        "views/my2_event_banner_views.xml",
        "views/partner_compassion_view.xml",
        "views/product_view.xml",
        "views/correspondence_view.xml",
        "views/correspondence_prewritten_letter.xml",
        "views/my2_header_menu.xml",
        "data/signup_email_confirmation.xml",
        "data/communication_config.xml",
        "data/dynamic_stylesheets.xml",
        # My Compassion 2 pages
        "templates/pages/my2_children.xml",
        "templates/pages/my2_child_timeline.xml",
        "templates/pages/my2_child_letters.xml",
        "templates/pages/my2_dashboard.xml",
        "templates/pages/my2_donations.xml",
        "templates/pages/my2_donation_details.xml",
        "templates/pages/my2_new_letter.xml",
        "templates/pages/my2_user_settings.xml",
        "templates/pages/my2_login_template.xml",
        "templates/pages/my2_gifts.xml",
        "templates/pages/my2_sponsorships.xml",
        "templates/pages/my2_new_sponsorship_wizard.xml",
        "templates/pages/my2_gift_package.xml",
        "templates/pages/my2_gifts_thank_you.xml",
        "templates/pages/my2_add_a_gift.xml",
        "templates/http_error_custom.xml",
        "templates/pages/my2_contact_us.xml",
        "templates/pages/my2_contactus_thank_you.xml",
        "templates/pages/child_protection_override.xml",
        # My Compassion 2 components
        "templates/components/my2_children_card.xml",
        "templates/components/my2_letter_card.xml",
        "templates/components/my2_breadcrumbs.xml",
        "templates/components/my2_sponsor_child_timeline_batch.xml",
        "templates/components/my2_donation_item.xml",
        "templates/components/my2_donation_product.xml",
        "templates/components/my2_donation_form.xml",
        "templates/components/my2_giving_limits_table.xml",
        "templates/components/my2_giving_limits_modal.xml",
        "templates/components/my2_checkout.xml",
        "templates/components/my2_weather_time_container.xml",
        # Other data the depends on the templates
        "data/my2_new_sponsorship_wizard_steps.xml",
    ],
    "depends": [
        "partner_communication_compassion",
        "wordpress_configuration",
        "sponsorship_sub_management",
        "web",
        "website_sale",
        "website_child_protection",
        "website_sponsorship",
        "website_form",
        "gift_compassion",
        "auth_signup",
        "http_routing",
        "website",
        "website_crm_privacy_policy",  # OCA/website
        "auth_signup_verify_email",  # OCA/server-auth
        "queue_job",
        "theme_compassion_2025",
        "utm",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
