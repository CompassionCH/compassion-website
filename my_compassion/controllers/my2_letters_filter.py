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
    def get_letters(self, child_id, **kwargs):
        domain = [("child_id", "=", child_id)]

        letters = request.env["correspondence"].search(
            domain, order="scanned_date DESC"
        )
        result_letters = []

        for letter in letters:
            html = request.env["ir.qweb"]._render(
                "my_compassion.my2_letter_card_component", {"letter": letter}
            )
            result_letters.append(
                {
                    "uuid": letter.uuid,
                    "direction": letter.direction,
                    "generator_id": letter.generator_id.id,
                    "scanned_date": letter.scanned_date,
                    "name": letter.name,
                    "html": html,
                }
            )

        return {"letters": result_letters}

    @http.route(
        ["/my2/children/<int:child_id>/filter_letters"],
        type="json",
        auth="user",
        website=True,
    )
    def filter_letters(
        self,
        child_id,
        start_date=None,
        end_date=None,
        direction=None,
        sort_order="desc",
    ):
        domain = [("child_id", "=", child_id)]

        if start_date and end_date:
            domain += [
                ("scanned_date", ">=", start_date),
                ("scanned_date", "<=", end_date),
            ]

        if direction in ["Supporter To Beneficiary", "Beneficiary To Supporter"]:
            domain += [("direction", "=", direction)]

        letters = request.env["correspondence"].search(
            domain, order="scanned_date " + sort_order
        )

        result_letters = []
        for letter in letters:
            html = request.env["ir.qweb"]._render(
                "my_compassion.my2_letter_card_component", {"letter": letter}
            )
            result_letters.append(
                {
                    "html": html,
                    "scanned_date": fields.Date.to_string(letter.scanned_date),
                    "direction": letter.direction,
                }
            )

        return {"letters": result_letters}
