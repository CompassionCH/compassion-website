##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models


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
            letter._notify_new_letter()
        return result
