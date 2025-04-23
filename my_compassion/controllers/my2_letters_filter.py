##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Marco Luca Centamori <mcentamori@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request

class My2LettersFilter(http.Controller):

    @http.route(['/my2/children/<int:child_id>/filter_supporter_to_beneficiary'], type='json', auth='user', website=True)
    def filter_supporter_to_beneficiary(self, child_id, **kwargs):
        domain = [
            ('child_id', '=', child_id),
            ('direction', '=', 'Supporter To Beneficiary')
        ]
        return self._get_filtered_letters(domain)

    @http.route(['/my2/children/<int:child_id>/filter_beneficiary_to_supporter'], type='json', auth='user', website=True)
    def filter_beneficiary_to_supporter(self, child_id, **kwargs):
        domain = [
            ('child_id', '=', child_id),
            ('direction', '=', 'Beneficiary To Supporter')
        ]
        return self._get_filtered_letters(domain)

    def _get_filtered_letters(self, domain):
        letters = request.env['correspondence'].search(domain, order="scanned_date DESC")
        result_letters = []

        for letter in letters:
            # Use qweb_render instead of render_template
            html = request.env['ir.qweb']._render(
                'my_compassion.my2_letter_card_component',
                {'letter': letter}
            )
            result_letters.append({
                'direction': letter.direction,
                'scanned_date': letter.scanned_date,
                'html': html
            })

        return {'letters': result_letters}

    @http.route(['/my2/children/<int:child_id>/get_all_letters'], type='json', auth='user', website=True)
    def get_all_letters(self, child_id, **kwargs):
        domain = [('child_id', '=', child_id)]
        return self._get_filtered_letters(domain)