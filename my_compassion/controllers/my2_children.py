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

        breadcrumbs = [
            {'name': 'Children', 'url': '/my2/children/', 'active': True},
        ]

        return request.render(
            'my_compassion.my2_children_page',
            {
                'sponsorship_ids': partner.sponsorship_ids,
                'breadcrumbs': breadcrumbs,
            }
        )

    @http.route('/my2/children/<int:child_id>', type="http", auth="user", website=True)
    def my2_render_child_timeline_page(self, child_id, **kwargs):
        partner = request.env.user.partner_id
        offset = int(kwargs.get('offset', 0))
        limit = int(kwargs.get('limit', 9))

        #################################
        ###     CHILD INFORMATION     ###
        #################################
        # Get the sponsored child directly from the partner's sponsorships
        child = partner.sponsorship_ids.filtered(lambda s: s.child_id.id == child_id).mapped('child_id')

        if not child:
            return request.redirect('/my2/children')  # fallback or 404

        #################################
        ###          TIMELINE         ###
        #################################

        # Prepare the domain to filter timeline records for the specific child and partner
        domain = [
            ('child_id', '=', child_id),
            ('partner_id', '=', partner.id)
        ]

        # Fetch the timeline records for the child, ordered by creation date (desc)
        timeline = request.env['compassion.sponsor_child_timeline'].sudo()
        total = timeline.search_count(domain)
        records = timeline.search(domain, order='create_date desc', offset=offset, limit=limit)

        # debugging output each records metadata and content
        for record in records:
            print(
                f"Record ID: {record.id}, Model: {record.model}, Metadata: {record.metadata}, Content: {record.content}")

        #################################
        ###        BREADCRUMBS        ###
        #################################
        breadcrumbs = [
            {'name': 'Children', 'url': '/my2/children/', 'active': False},
            {'name': child[0].preferred_name, 'url': f'/my2/children/{child[0].id}', 'active': True},
        ]

        # Render the child timeline page with the collected data
        return request.render('my_compassion.my2_child_timeline_page', {
            'compassion_child': child,
            'breadcrumbs': breadcrumbs,
            'records': records,
            'pageable': {
                'offset': offset,
                'limit': limit,
                'total': total,
                'has_more_records': total > offset + limit
            }
        })


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
