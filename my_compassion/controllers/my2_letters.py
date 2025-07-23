##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from lark.load_grammar import nr_deepcopy_tree
from odoo.http import request
from odoo import http
from datetime import date


class MyCompassionCorrespondenceController(http.Controller):

    @http.route(['/my2/children/letters', '/my2/children/letters/<int:child_id>'],
                type="http", auth="user",
                website=True, sitemap=False)
    def my2_render_child_letters_page(self, child_id=None, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id
        current_year = date.today().year
        filter_child = next(
            (c for c in children_sponsored_by_partner if c.id == child_id), None)

        # Helper function to safely parse integers from query params
        def safe_int(value, default):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        # Filtering params
        page = safe_int(kwargs.get('page'), 1)
        year_from = safe_int(kwargs.get('year_from'), 1900)
        year_to = safe_int(kwargs.get('year_to'), current_year)
        month_from = safe_int(kwargs.get('month_from'), 1)
        month_to = safe_int(kwargs.get('month_to'), 12)
        letter_type = kwargs.get('type')
        sort_order = kwargs.get('sort', 'newest')
        nr_filters_applied = 0

        # Build filter date range
        import calendar
        last_day = calendar.monthrange(year_to, month_to)[1]
        from_date = date(year_from, month_from, 1)
        to_date = date(year_to, month_to, last_day)

        # Build the domain of the filtering of the letters
        filter_domain = [("partner_id", "=", partner.id)]

        if filter_child:
            filter_domain.append(("child_id", "=", child_id))
            nr_filters_applied += 1
        filter_domain.append(("create_date", ">=", from_date))
        filter_domain.append(("create_date", "<=", to_date))
        if year_from > 1900 or year_to < current_year or month_from > 1 or month_to < 12:
            nr_filters_applied += 1
        if letter_type:
            filter_domain.append(("direction", "=", letter_type))
            nr_filters_applied += 1
        order = "create_date DESC" if sort_order == "newest" else "create_date ASC"
        if sort_order == "oldest":
            nr_filters_applied += 1

        # Pagination setup
        letters_per_page = 24
        offset = (page - 1) * letters_per_page
        total_letters = request.env['correspondence'].search_count(filter_domain)
        total_pages = max(1, -(-total_letters // letters_per_page))

        letters = request.env['correspondence'].search(
            filter_domain,
            order=order,
            offset=offset,
            limit=letters_per_page
        )

        # Fetch the filtered letters from the database
        letter_children_pairs = []
        for letter in letters:
            if letter.child_id:
                letter_children_pairs.append((letter, letter.child_id))

        return request.render(
            'my_compassion.my2_child_letters_page',
            {
                'child_id': child_id,
                'letter_children_pairs': letter_children_pairs,
                'filter_child': filter_child,
                'current_year': current_year,
                'children_list': children_sponsored_by_partner,
                'current_page': page,
                'total_pages': total_pages,
                'filters': {
                    'year_from': year_from,
                    'year_to': year_to,
                    'month_from': month_from,
                    'month_to': month_to,
                    'type': letter_type,
                    'sort': sort_order,
                },
                'nr_filters_applied': nr_filters_applied
            }
        )

@http.route('/my2/children/<int:child_id>/letter/new', type="http", auth="user",
            website=True, sitemap=False)
def my2_render_new_letter_page(self, child_id, **kwargs):
    partner = request.env.user.partner_id
    children_sponsored_by_partner = partner.sponsorship_ids.child_id

    # Retrieve the child object already instantiated
    selected_child = None
    for compassion_child in children_sponsored_by_partner:
        if compassion_child.id == child_id:
            selected_child = compassion_child

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

    breadcrumbs = [
        {'name': 'Children', 'url': '/my2/children/', 'active': False},
        {'name': 'New Letter', 'url': '/my2/children/' + str(child_id) + '/letter/new',
         'active': True},
    ]

    return request.render(
        'my_compassion.my2_new_letter_page',
        {
            'selected_child': selected_child,
            'sponsorship_ids': partner.sponsorship_ids,
            'templates': templates,
            'breadcrumbs': breadcrumbs,
        }
    )


@http.route('/my2/children/letter/new', type="json", auth="user", methods=['POST'],
            sitemap=False)
def my2_create_new_letter(self, **post):
    """
        Used in my2_new_letter.js for sending the new letter form data
    """

    # Retrieve JSON data
    child_id = int(post.get('child_id'))
    template_id = post.get('template_id')
    letter_body = post.get('letter_body')
    source = post.get('source')
    csrf_token = post.get('csrf_token')  # Should we use it somehow?
    attachments = post.get('attachments')
    mode = post.get('mode')  # Either send or preview

    # Retrieve related user data
    partner = request.env.user.partner_id
    children_sponsored_by_partner = partner.sponsorship_ids.child_id

    # Retrieve the child object already instantiated
    selected_child = None
    for compassion_child in children_sponsored_by_partner:
        if compassion_child.id == child_id:
            selected_child = compassion_child

    # This is from legacy, it should be refactored in my opinion
    datas = []
    for file in attachments:
        if isinstance(file, dict) and "content" in file:
            datas.append(
                (
                    0,
                    0,
                    {
                        "datas": file["content"],
                        "name": file["filename"],
                    },
                )
            )

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
        "image_ids": datas,
        "source": source,
    }

    # Retrieved code from legacy, wondering use case ?
    language = request.env["langdetect"].sudo().detect_language(letter_body)
    if language:
        letter_values["language_id"] = language.id

    letter_generator = request.env["correspondence.s2b.generator"].sudo().create(
        letter_values)

    # I don't understand why was it made like this
    # This is how legacy retrieves the sponsorship_id...
    letter_generator.onchange_domain()

    letter_generator.preview()

    if mode == 'send':
        letter_generator.generate_letters_job()

    if letter_generator:

        return {
            "preview_url": f"{request.httprequest.host_url}web/image/{letter_generator._name}/{letter_generator.id}/preview_pdf",
            "letter_values": letter_values,
            "generator_id": letter_generator.id,
        }

    else:
        return {
            "error": "Something went wrong.",
        }
