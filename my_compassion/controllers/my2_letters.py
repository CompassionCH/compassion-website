##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request
from odoo import http


class MyCompassionCorrespondenceController(http.Controller):

    @http.route('/my2/children/<int:child_id>/letters', type="http", auth="user",
                website=True)
    def my2_render_child_letters_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        letters = request.env['correspondence'].search(
            [
                ("partner_id", "=", partner.id)
            ],
            order="scanned_date DESC"
        )

        for compassion_child in children_sponsored_by_partner:
            if compassion_child.id == child_id:
                return request.render(
                    'my_compassion.my2_child_letters_page',
                    {
                        'compassion_child': compassion_child,
                        'letters': letters,
                    }
                )

    @http.route('/my2/children/<int:child_id>/letter/new', type="http", auth="user", website=True)
    def my2_render_new_letter_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        # Retrieve the child object already instantiated
        selected_child = None
        for compassion_child in children_sponsored_by_partner:
            if compassion_child.id == child_id:
                selected_child= compassion_child

        return request.render(
            'my_compassion.my2_new_letter_page',
            {
                'selected_child': selected_child,
                'sponsorship_ids': partner.sponsorship_ids,
            }
        )
