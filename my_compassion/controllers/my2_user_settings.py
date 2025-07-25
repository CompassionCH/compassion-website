##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nicolò Hepp <nhepp@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request
from odoo import http

class MyCompassionUserController(http.Controller):

    @http.route('/my2/user_settings', type="http", auth="user", website=True, sitemap=False)
    def my2_render_user_settings_page(self, **kwargs):
        partner = request.env.user.partner_id
        currently_editing_info = request.params.get('currently_editing_info') == 'true'
        submitted_info_edited = request.params.get('submitted_info_edited') == 'true'

        # TODO: check if there is alredady an old script for this
        def is_valid_phone(phone):
            return False
        def is_valid_email(email):
            return False

        # Define accepted fields structure
        profile_edits_accepted_fields = {
            'title': False,
            'surname': False,
            'name': False,
            'city': False,
            'zip': False,
            'phone': False,
            'email': False,
        }

        # Check if any field has a value (user attempted to submit something)
        if submitted_info_edited:
            # Go field by field, check if any value is submitted and valid
            title = request.params.get('title_change')
            if title and title != '':
                profile_edits_accepted_fields['title'] = True
            if request.params.get('surname_change', '').strip():
                profile_edits_accepted_fields['surname'] = True
            if request.params.get('name_change', '').strip():
                profile_edits_accepted_fields['name'] = True
            if request.params.get('zip_change', '').strip():
                profile_edits_accepted_fields['zip'] = True
            if request.params.get('city_change', '').strip():
                profile_edits_accepted_fields['city'] = True
            phone = request.params.get('phone_change', '').strip()
            if phone and is_valid_phone(phone):
                profile_edits_accepted_fields['phone'] = True
            email = request.params.get('email_change', '').strip()
            if email and is_valid_email(email):
                profile_edits_accepted_fields['email'] = True

            # If all fields are accepted, set the variable to False
            currently_editing_info = not all(profile_edits_accepted_fields.values())

        return request.render(
            'my_compassion.my2_user_settings_page',
            {
                'partner': partner,
                'currently_editing_info': currently_editing_info,
                'submitted_info_edited': submitted_info_edited,
                'profile_edits_accepted_fields': profile_edits_accepted_fields,
            }
        )