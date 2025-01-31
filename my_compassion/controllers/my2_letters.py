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

        # Retrieve the letter templates
        templates = (
            request.env["correspondence.template"].search(
                [
                    ("active", "=", True),
                    ("website_published", "=", True),
                ]
            )
            # Sort the templates alphabetically, placing "Christmas" templates at the beginning
            # "0" is special sorting key because it comes before any letter in ASCII order.
            .sorted(lambda t: "0" if "christmas" in t.name.lower() else t.name)
        )

        return request.render(
            'my_compassion.my2_new_letter_page',
            {
                'selected_child': selected_child,
                'sponsorship_ids': partner.sponsorship_ids,
                'templates': templates,
            }
        )

    @http.route('/my2/children/letter/new', type="json", auth="user", methods=['POST'])
    def my2_create_new_letter(self, **post):
        """
            Used in my2_new_letter.js for sending the new letter form data
        """

        # Retrieve JSON data
        child_id = int(post.get('child_id'))
        template_id = post.get('template_id')
        letter_body = post.get('letter_body')
        source = post.get('source')
        csrf_token = post.get('csrf_token') # Should we use it somehow?
        attachments = post.get('attachments')

        # Retrieve related user data
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id

        # Retrieve the child object already instantiated
        selected_child = None
        for compassion_child in children_sponsored_by_partner:
            if compassion_child.id == child_id:
                selected_child = compassion_child

        letter_values = {
            "name": f"{source}-{selected_child.local_id}",
            "selection_domain": str(
                [
                    ("child_id.local_id", "=", selected_child.local_id),
                    ("state", "not in", ["draft", "cancelled"]),
                ]
            ),
            "body": letter_body,
            "template_id": int(template_id),
            "image_ids": attachments,
            "source": source,
        }

        letter_generator = request.env["correspondence.s2b.generator"].sudo().create(letter_values)
        letter_generator.generate_letters()

        return {
            "preview_url": f"{request.httprequest.host_url}/web/image/{letter_generator._name}/{letter_generator.id}/preview_pdf",
            "letter_values": letter_values,
        }
