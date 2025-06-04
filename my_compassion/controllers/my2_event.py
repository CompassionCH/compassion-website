##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Marco Centamori <mcentamori@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request, route


class MyCompassionCorrespondenceController(http.Controller):

    @http.route('/my2/children/<int:child_id>', type='http', auth='user', website=True)
    def my2_child_timeline(self, child_id, **kwargs):
        child = request.env['compassion.child'].browse(child_id)
        sponsorship = request.env['sponsorship'].search(
            [('child_id', '=', child_id), ('partner_id', '=', request.env.user.partner_id.id)], limit=1)
        has_unread_letter = False
        if sponsorship:
            has_unread_letter = bool(
                request.env['correspondence'].search([
                    ('child_id', '=', child_id),
                    ('email_read', '=', False),
                ], limit=1)
            )
        return request.render(
            'my_compassion.my2_child_timeline_page',
            {
                'child': child,
                'sponsorship': sponsorship,
                'has_unread_letter': has_unread_letter,
            }
        )
