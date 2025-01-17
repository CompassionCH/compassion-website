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


class MyCompassionChildrenController(http.Controller):

    @http.route('/my2/children/', type="http", auth="user", website=True)
    def my2_render_children_page(self, **kwargs):
        """
        Renders the children page related to the logged-in user's sponsorships.
        return: An HTTP response containing a rendered template with sponsorship data.
        """
        partner = request.env.user.partner_id

        return request.render(
            'my_compassion.my2_children_page',
            {
                'sponsorship_ids': partner.sponsorship_ids,
            }
        )

    @http.route('/my2/children/<int:child_id>', type="http", auth="user", website=True)
    def my2_render_child_timeline_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        for child in children_sponsored_by_partner:
            if child.id == child_id:
                return request.render(
                    'my_compassion.my2_child_timeline_page',
                    {
                        'compassion_child': child,
                    }
                )

    @http.route('/my2/children/<int:child_id>/details', type="http", auth="user", website=True)
    def my2_render_child_details_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        for child in children_sponsored_by_partner:
            if child.id == child_id:
                return request.render(
                    'my_compassion.my2_child_details_page',
                    {
                        'compassion_child': child,
                    }
                )





