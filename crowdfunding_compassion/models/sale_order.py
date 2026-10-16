##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        """A donation to a participant: the project is the campaign of the
        invoice, the participant its source."""
        vals = super()._prepare_invoice()
        participant = self.order_line.participant_id[:1]
        if participant:
            vals["campaign_id"] = (
                vals.get("campaign_id") or participant.project_id.campaign_id.id
            )
            vals["source_id"] = vals.get("source_id") or participant.source_id.id
            vals["medium_id"] = (
                vals.get("medium_id") or self.env.ref("utm.utm_medium_website").id
            )
        return vals
