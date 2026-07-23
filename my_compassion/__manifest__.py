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
    "version": "18.0.1.0.16",
    "category": "Website",
    "author": "Compassion CH",
    "license": "AGPL-3",
    "website": "https://github.com/CompassionCH/compassion-website",
    "data": [
        "security/access_rules.xml",
        "security/ir.model.access.csv",
        # My Compassion 2 data
        "data/account_payment_method.xml",
        "data/digital_charge_cron.xml",
        "data/my2_website.xml",
        "data/auto_letter_templates_updater_cron.xml",
        # My compassion 2 assets, needs to be placed before others
        "templates/my2_assets.xml",
        "templates/my_account_components.xml",
        "templates/my_account_personal_info.xml",
        "templates/my_account_donations.xml",
        "templates/signup.xml",
        "templates/my2_change_password.xml",
        "views/correspondence_template_view.xml",
        "views/my2_event_banner_views.xml",
        "views/partner_compassion_view.xml",
        "views/product_view.xml",
        "views/correspondence_view.xml",
        "views/correspondence_prewritten_letter.xml",
        "views/my2_header_menu.xml",
        "views/child_view.xml",
        "views/payment_mode_view.xml",
        "views/account_move_view.xml",
        "views/contract_origin_view.xml",
        "data/signup_email_confirmation.xml",
        "data/communication_config.xml",
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
        "templates/pages/my2_new_sponsorship_payment.xml",
        "templates/pages/my2_update_card.xml",
        "templates/pages/my2_gift_package.xml",
        "templates/pages/my2_gifts_thank_you.xml",
        "templates/pages/my2_add_a_gift.xml",
        "templates/http_error_custom.xml",
        "templates/pages/my2_contact_us.xml",
        "templates/pages/my2_contactus_thank_you.xml",
        "templates/pages/child_protection_override.xml",
        "templates/pages/child_unavailable_page.xml",
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
        "sponsorship_sub_management",
        "web",
        "website_sale",
        "website_child_protection",
        "child_compassion",
        "partner_auto_match",
        "partner_search_fuzzy",
        "website_legal_page",  # OCA/website
        "gift_compassion",
        "auth_signup",
        "http_routing",
        "website",
        "auth_signup_verify_email",  # OCA/server-auth
        "theme_compassion_2025",
        "utm",
    ],
    "assets": {
        "web.assets_frontend": [
            "my_compassion/static/src/css/global.css",
            "my_compassion/static/src/css/toast_notification.css",
            "my_compassion/static/src/css/my2_children_card.css",
            "my_compassion/static/src/css/my2_donation_item.css",
            "my_compassion/static/src/css/my2_donation_product.css",
            "my_compassion/static/src/css/my2_donation_form.css",
            "my_compassion/static/src/css/my2_donation_details.css",
            "my_compassion/static/src/css/my2_add_a_gift.css",
            "my_compassion/static/src/css/my2_gift_package.css",
            "my_compassion/static/src/css/my2_donations.css",
            "my_compassion/static/src/css/my2_gifts_thank_you.css",
            "my_compassion/static/src/css/my2_giving_limits_table.css",
            "my_compassion/static/src/css/my2_giving_limits_modal.css",
            "my_compassion/static/src/css/login.css",
            "my_compassion/static/src/css/my2_sponsorships.css",
            "my_compassion/static/src/css/my2_new_sponsorship_wizard.css",
            "my_compassion/static/src/css/template_image.css",
            "my_compassion/static/src/css/add_a_picture_input.css",
            "my_compassion/static/src/css/delete_a_picture_input.css",
            "my_compassion/static/src/css/child_letters.css",
            "my_compassion/static/src/css/letter_card.css",
            "my_compassion/static/src/css/child_profile.css",
            "my_compassion/static/src/css/child_profile_timeline.css",
            "my_compassion/static/src/css/my2_weather_time_container.css",
            "my_compassion/static/src/css/user_settings.css",
            # ES module JS
            "my_compassion/static/src/js/toast_service.js",
            "my_compassion/static/src/js/show_password.js",
            "my_compassion/static/src/js/my2_donation_form.js",
            "my_compassion/static/src/js/my2_donation_details.js",
            "my_compassion/static/src/js/my2_add_a_gift.js",
            "my_compassion/static/src/js/my2_gift_package.js",
            "my_compassion/static/src/js/my2_donations.js",
            "my_compassion/static/src/js/my2_sponsorships.js",
            "my_compassion/static/src/js/my2_new_sponsorship_wizard.js",
            "my_compassion/static/src/js/my2_letter_attachments.js",
            "my_compassion/static/src/js/my2_new_letter_add_a_picture_input.js",
            "my_compassion/static/src/js/my2_new_letter_clear_button.js",
            "my_compassion/static/src/js/my2_new_letter.js",
            "my_compassion/static/src/js/my2_new_letter_child_selector_image.js",
            "my_compassion/static/src/js/my2_new_letter_template_image_selection.js",
            "my_compassion/static/src/js/my2_letter_template_loader.js",
            "my_compassion/static/src/js/my2_child_letters.js",
            "my_compassion/static/src/js/my2_child_letters_card_behavior.js",
            "my_compassion/static/src/js/child_profile_tabs.js",
            "my_compassion/static/src/js/child_profile_timeline.js",
            "my_compassion/static/src/js/my2_child_center_weather_time.js",
            "my_compassion/static/src/js/error_page_redirect.js",
            "my_compassion/static/src/js/my2_user_settings.js",
            # client templates
            "my_compassion/static/src/xml/toast_notification.xml",
        ],
        "web.assets_tests": [
            "my_compassion/static/src/js/tours/donation_tour.js",
        ],
    },
    "demo": [],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
}
