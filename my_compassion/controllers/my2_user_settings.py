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
from odoo.exceptions import ValidationError


class MyCompassionUserController(http.Controller):

    @http.route('/my2/user_settings', type="http", auth="user", website=True)
    def render_user_settings_page(self, **kwargs):
        partner = request.env.user.partner_id

        # Pre-fetch data for the template's selection fields.
        titles = request.env['res.partner.title'].sudo().search(
            [('is_published', '=', True)])
        countries = request.env['res.country'].sudo().search([])

        # Determines which tab should be active when the page loads.
        current_tab = kwargs.get('current_tab', 'personal-information')

        return request.render('my_compassion.my2_user_settings_page', {
            'user': request.env.user,
            'partner': partner,
            'titles': titles,
            'countries': countries,
            'current_tab': current_tab,
        })

    @http.route('/my2/user_settings/set_personal_info', type="json", auth="user",
                methods=["POST"], website=True)
    def set_personal_info(self, **post):
        partner = request.env.user.partner_id
        # A whitelist of fields that are allowed to be updated through this endpoint.
        allowed_fields = {
            'title': int, 'lastname': str, 'firstname': str, 'street': str,
            'city': str, 'country_id': int, 'zip': str, 'phone': str, 'email': str
        }

        vals_to_update = {}
        errors = {}
        # Iterate through submitted data and validate it against the allowed fields.
        for field, value in post.items():
            if field in allowed_fields:
                clean_value = (value or '').strip()
                if not clean_value:
                    errors[field] = "This field cannot be empty."
                else:
                    try:
                        vals_to_update[field] = allowed_fields[field](clean_value)
                    except (ValueError, TypeError):
                        errors[field] = "Invalid value for %s." % field

        if errors:
            # If any errors were found, return them to the frontend. Do not update the record.
            return {'success': False, 'errors': errors}

        if vals_to_update:
            # When an address component is changed, reset the linked zip_id
            if any(k in vals_to_update for k in ['city', 'zip', 'country_id']):
                vals_to_update['zip_id'] = False
            try:
                partner.sudo().write(vals_to_update)
            except ValidationError as e:
                if 'email' in vals_to_update:
                    return {'success': False, 'errors': {'email': e.args[0]}}

        return {'success': True}

    @http.route('/my2/user_settings/set_account_settings', type="json", auth="user",
                methods=["POST"], website=True)
    def set_account_settings(self, **post):
        user = request.env.user
        new_login = (post.get('login') or '').strip()

        if not new_login:
            return {'success': False, 'errors': {'login': "Login cannot be empty."}}

        # Check if login is already taken by another user
        if request.env['res.users'].sudo().search_count(
                [('login', '=', new_login), ('id', '!=', user.id)]):
            return {'success': False, 'errors': {
                'login': "This email is already used as a login by another user."}}

        user.sudo().write({'login': new_login})
        return {'success': True}

    @http.route("/my2/user_settings/agree_child_protection_charter", type="json",
                auth="user", methods=["POST"])
    def agree_child_protection_charter(self, **post):
        request.env.user.partner_id.sudo().write({
            'date_agreed_child_protection_charter': date.today()
        })
        return {'success': True}

    @http.route("/my2/user_settings/set_communication_settings", type="json",
                auth="user", methods=["POST"])
    def set_partner_communication_settings(self, **post):
        partner = request.env.user.partner_id
        # A whitelist of allowed communication preference fields.
        allowed_fields = {
            'opt_out', 'tax_receipt_preference', 'letter_delivery_preference',
            'photo_delivery_preference', 'calendar', 'birthday_reminder',
            'sponsorship_anniversary_card'
        }

        update_vals = {}
        for field, value in post.items():
            if field in allowed_fields:
                # Convert string booleans from JS
                if isinstance(value, bool):
                    update_vals[field] = value
                elif str(value).lower() in ['true', 'false']:
                    update_vals[field] = (str(value).lower() == 'true')
                else:
                    update_vals[field] = value

        if update_vals:
            partner.sudo().write(update_vals)

        return {'success': True}
