##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)

# Communications about invoices: thank-you letters and donation receipts.
NAMED_COMMUNICATION_MODELS = ("account.move", "account.move.line")


class CommunicationJob(models.Model):
    _inherit = "partner.communication.job"

    def send(self):
        """No thank-you letter or receipt for a donor known by email only: it
        would greet "(pending)". It stays pending until the donor gives their
        name, which sends the automatic ones (_my2_release_held). It never
        raises: the automatic send runs in a queue job, and partner_communication
        sends a communication again when another one is merged into it. Sent
        alone, it tells the user why it waits. The fast checkout's own emails
        are not held."""
        held = self.filtered(
            lambda j: j.state == "pending"
            and j.model in NAMED_COMMUNICATION_MODELS
            and j.partner_id.my2_name_placeholder
        )
        if held:
            _logger.info(
                "Communications %s wait for the real name of their donor.",
                held.ids,
            )
        if held and held == self and len(self) == 1:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "message": _(
                        "The donor has not given their name yet: this communication"
                        " waits for it."
                    ),
                },
            }
        return super(CommunicationJob, self - held).send()

    def _my2_release_held(self):
        """What waited for the donor's real name: the text, rendered when the
        communication was created, is rendered again with it, and the
        automatic ones are sent, in a queue job as at their creation - one
        per communication: several of one rule may wait for one donor. The
        others wait for staff, as any pending communication."""
        self.refresh_text()
        for job in self.filtered("auto_send"):
            job.with_delay_sh(
                "send",
                eta=10,
                max_retries=1,
                description="Autosend communication",
                channel="root.partner_communication",
                identity_key=f"{self._name}.send.{job.id}",
            )
