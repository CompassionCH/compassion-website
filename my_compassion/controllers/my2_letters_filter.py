##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Marco Luca Centamori <mcentamori@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, http
from odoo.http import request


class My2LettersFilter(http.Controller):
    @http.route(
        ["/my2/children/<int:child_id>/get_letters"],
        type="json",
        auth="user",
        website=True,
    )
    # This route retrieves all letters for a specific child.
    # Called from the frontend to display letters (see my_compassion/static/src/js/my2_letters_filter.js)

    def get_letters(self, child_id, **kwargs):
        domain = [("child_id", "=", child_id)]

        letters = request.env["correspondence"].search(
            domain, order="scanned_date DESC"
        )
        result_letters = []

        for letter in letters:
            result_letters.append(
                {
                    "uuid": letter.uuid,
                    "direction": letter.direction,
                    "generator_id": letter.generator_id.id,
                    "scanned_date": letter.scanned_date,
                    "name": letter.name,
                }
            )

        return {"letters": result_letters}