##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nicolò Hepp <nhepp@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request
from datetime import date


class MyCompassionUserController(http.Controller):

    @http.route('/my2/user_settings', type="http", auth="user", website=True,
                sitemap=False)
    def my2_render_user_settings_page(self, **kwargs):
        partner = request.env.user.partner_id
        params = request.params
        titles = request.env['res.partner.title'].sudo().search(
            [('is_published', '=', True)])
        countries = request.env['res.country'].sudo().search([])

        # Flags
        currently_editing_info = params.get('currently_editing_info') == 'true'
        submitted_info_edited = params.get('submitted_info_edited') == 'true'
        sign_confirm = params.get('sign_confirm') == 'true'

        # Save child protection charter signature
        if sign_confirm:
            partner.write({'date_agreed_child_protection_charter': date.today()})

        # Handle profile info update
        profile_field_map = {
            'title_change': ('title', int),
            'surname_change': ('lastname', str),
            'name_change': ('firstname', str),
            'zip_change': ('zip', str),
            'country_id_change': ('country_id', int),
            'address_change': ('street', str),
            'city_change': ('city', str),
            'phone_change': ('phone', str),
            'email_change': ('email', str),
        }

        profile_edits_accepted = {key.split('_')[0]: False for key in profile_field_map}
        profile_updates = {}

        if submitted_info_edited:
            for param_key, (field_name, cast_type) in profile_field_map.items():
                raw_value = params.get(param_key, '').strip()
                if raw_value:
                    try:
                        new_value = cast_type(raw_value)
                        original_value = partner[field_name]

                        if hasattr(original_value, 'id'):
                            original_value = original_value.id

                        if new_value != original_value:
                            profile_updates[field_name] = new_value

                        profile_edits_accepted[param_key.split('_')[0]] = True
                    except (ValueError, TypeError):
                        continue

            if profile_updates.get('city') or profile_updates.get(
                    'country_id') or profile_updates.get('zip'):
                profile_updates["zip_id"] = False

            if all(profile_edits_accepted.values()):
                partner.write(profile_updates)
                partner = request.env['res.partner'].browse(partner.id)
            else:
                currently_editing_info = True

        return request.render('my_compassion.my2_user_settings_page', {
            'partner': partner,
            'titles': titles,
            'countries': countries,
            'currently_editing_info': currently_editing_info,
            'submitted_info_edited': submitted_info_edited,
            'profile_edits_accepted_fields': profile_edits_accepted,
        })



class MyCompassionUserController(http.Controller):

    @http.route(
        "/my2/user_settings/set_communication_settings",
        type="json",
        auth="user",
        methods=["POST"],
        sitemap=False,
    )
    def my2_set_partner_communication_settings(self, **post):
        partner = request.env.user.partner_id

        allowed_fields = {
            'tax_receipt_preference',
            'letter_delivery_preference',
            'photo_delivery_preference',
            'calendar',
            'birthday_reminder',
            'sponsorship_anniversary_card',
        }

        update_vals = {}

        for field, value in post.items():
            if field not in allowed_fields:
                continue

            if value in ['true', 'false']:
                value = value == 'true'

            update_vals[field] = value

        if update_vals:
            partner.write(update_vals)

        return {}
