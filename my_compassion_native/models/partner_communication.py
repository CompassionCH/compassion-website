##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class CommunicationJob(models.Model):
    _inherit = "partner.communication.job"

    def _job_sent(self, send_mode):
        """Push the new-letter notification only once the letter is readable.

        Publication needs the communication to reach "done", so notifying from
        correspondence.process_letter() pushed sponsors towards a letter that
        was not in their list yet - and stayed unreachable whenever the
        communication was skipped or failed.
        """
        result = super()._job_sent(send_mode)
        letters = self.env["correspondence"].search(
            [("communication_id", "in", self.ids)]
        )
        for letter in letters.filtered("is_published"):
            # The letter has already left: a failed push must not roll back
            # the communication's "done" state.
            try:
                with self.env.cr.savepoint():
                    letter._notify_new_letter()
            except Exception:
                _logger.exception("New-letter push failed for letter %s", letter.id)
        return result
