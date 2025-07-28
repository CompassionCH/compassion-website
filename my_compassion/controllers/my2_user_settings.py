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
        titles = request.env['res.partner.title'].sudo().search([('is_published', '=', True)])

        field_map = {
            'title_change':     ('title', int),
            'surname_change':   ('lastname', str),
            'name_change':      ('firstname', str),
            'city_change':      ('city', str),
            'address_change':   ('street', str),
            'zip_change':       ('zip', str),
            'phone_change':     ('phone', str),
            'email_change':     ('email', str),
        }

        profile_edits_accepted_fields = {key.split('_')[0]: False for key in field_map}
        update_values = {}

        if submitted_info_edited:
            for param, (field_name, cast_type) in field_map.items():
                raw_value = request.params.get(param, '').strip()
                if raw_value:
                    try:
                        update_values[field_name] = cast_type(raw_value)
                        profile_edits_accepted_fields[param.split('_')[0]] = True
                    except (ValueError, TypeError):
                        pass

            if all(profile_edits_accepted_fields.values()):
                partner.write(update_values)
                partner = request.env['res.partner'].browse(partner.id)

            currently_editing_info = not all(profile_edits_accepted_fields.values())

        return request.render(
            'my_compassion.my2_user_settings_page',
            {
                'partner': partner,
                'currently_editing_info': currently_editing_info,
                'submitted_info_edited': submitted_info_edited,
                'profile_edits_accepted_fields': profile_edits_accepted_fields,
                'titles': titles,
            }
        )