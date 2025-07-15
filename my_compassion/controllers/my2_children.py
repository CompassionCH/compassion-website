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

    @http.route('/my2/children/', type="http", auth="user", website=True, sitemap=False)
    def my2_render_children_page(self, **kwargs):
        """
        Renders the children page related to the logged-in user's sponsorships.
        return: An HTTP response containing a rendered template with sponsorship data.
        """
        partner = request.env.user.partner_id

        #To keep a list of the latest correspondence with each sponsored child:
        latest_correspondences_by_child_id = {}
        correspondences_table = request.env['correspondence'].sudo()

        received_correspondences = correspondences_table.search([
            ('partner_id', '=', partner.id),
            ('direction', '=', 'Beneficiary To Supporter'),
        ], order='write_date desc')

        for corr in received_correspondences:
            child_id = corr.child_id.id
            if child_id not in latest_correspondences_by_child_id:
                latest_correspondences_by_child_id[child_id] = corr

        breadcrumbs = [
            {'name': 'Children', 'url': '/my2/children/', 'active': True},
        ]

        return request.render(
            'my_compassion.my2_children_page',
            {
                'sponsorship_ids': partner.sponsorship_ids,
                'latest_correspondences_by_child_id': latest_correspondences_by_child_id,
                'breadcrumbs': breadcrumbs,
            }
        )

    @http.route('/my2/children/<int:child_id>', type="http", auth="user", website=True, sitemap=False)
    def my2_render_child_timeline_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        for child in children_sponsored_by_partner:
            if child.id == child_id:

                breadcrumbs = [
                    {'name': 'Children', 'url': '/my2/children/', 'active': False},
                    {'name': child.preferred_name, 'url': '/my2/children/' + str(child_id), 'active': True},
                ]

                return request.render(
                    'my_compassion.my2_child_timeline_page',
                    {
                        'compassion_child': child,
                        'breadcrumbs': breadcrumbs,
                    }
                )

    @http.route('/my2/children/<int:child_id>/details', type="http", auth="user", website=True, sitemap=False)
    def my2_render_child_details_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        for child in children_sponsored_by_partner:
            if child.id == child_id:

                breadcrumbs = [
                    {'name': 'Children', 'url': '/my2/children/', 'active': False},
                    {'name': child.preferred_name, 'url': '/my2/children/' + str(child_id), 'active': False},
                    {'name': 'Details', 'url': '/my2/children/' + str(child_id) + '/details', 'active': True},
                ]

                return request.render(
                    'my_compassion.my2_child_details_page',
                    {
                        'compassion_child': child,
                        'breadcrumbs': breadcrumbs,
                    }
                )
