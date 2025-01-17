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

        for child in children_sponsored_by_partner:
            if child.id == child_id:
                return request.render(
                    'my_compassion.my2_child_letters_page',
                    {
                        'compassion_child': child,
                    }
                )


