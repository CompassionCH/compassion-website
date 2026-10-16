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
        """A donation to a participant of an event: the event is the campaign
        of the invoice, the participant (fundraiser) its source."""
        vals = super()._prepare_invoice()
        registration = self.order_line.registration_id[:1]
        if registration:
            event = registration.compassion_event_id
            vals["campaign_id"] = vals.get("campaign_id") or event.campaign_id.id
            vals["source_id"] = (
                vals.get("source_id") or registration.source_id.id or event.source_id.id
            )
            vals["medium_id"] = (
                vals.get("medium_id") or self.env.ref("utm.utm_medium_website").id
            )
        return vals
