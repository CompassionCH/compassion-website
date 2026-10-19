##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Communications about invoices: thank-you letters and donation receipts.
NAMED_COMMUNICATION_MODELS = ("account.move", "account.move.line")


class CommunicationJob(models.Model):
    _inherit = "partner.communication.job"

    def send(self):
        """No thank-you letter or receipt for a donor known by email only: it
        would greet "(pending)". It stays pending until the donor gives their
        name (thank-you page, or the name the payment reports), and goes with
        the next sending. The fast checkout's own emails are not held."""
        held = self.filtered(
            lambda j: j.state == "pending"
            and j.model in NAMED_COMMUNICATION_MODELS
            and j.partner_id.my2_name_placeholder
        )
        if held and held == self and len(self) == 1:
            raise UserError(
                _(
                    "The donor has not given their name yet: this communication"
                    " waits for it."
                )
            )
        if held:
            _logger.info(
                "Communications %s wait for the real name of their donor.",
                held.ids,
            )
        return super(CommunicationJob, self - held).send()
