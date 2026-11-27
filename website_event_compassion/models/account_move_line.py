##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _received_donation_domain(self):
        """Donations whose money is received, for the barometer of a
        participant (event.registration._compute_amount_raised) and their
        donation list (MyEventsController.get_donations): the lines of a paid
        invoice, and the income lines of a bank statement line booked directly
        on the income account (reconciled without invoice), whose entry has no
        payment state. The bank journals reconcile in the "edit" mode, which
        books these lines on the move of the statement line. Price them with
        get_donation_amount()."""
        return [
            "|",
            ("payment_state", "=", "paid"),
            "&",
            "&",
            ("move_id.statement_line_id", "!=", False),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "in", ("income", "income_other")),
        ]
