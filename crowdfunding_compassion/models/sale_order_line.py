##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, models


class SaleOrderLine(models.Model):
    """Add salespersons to invoice_lines."""

    _inherit = "sale.order.line"

    participant_id = fields.Many2one("crowdfunding.participant")

    def _compute_cart_link(self):
        for line in self:
            if line.participant_id:
                line.cart_link = line.participant_id.website_url
            else:
                super(SaleOrderLine, line)._compute_cart_link()

    def get_donation_description(self, product):
        """Get the description for a donation."""
        if self.participant_id:
            if self.product_uom_qty > 1:
                return product.crowdfunding_quantity_plural
            return product.crowdfunding_quantity_singular
        return super().get_donation_description(product)

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        participant = getattr(self, "participant_id", False)
        analytic_id = participant.project_id.event_id.analytic_id.id
        if participant:
            res.update(
                {
                    "user_id": participant.partner_id.id,
                    "analytic_account_id": analytic_id,
                    "crowdfunding_participant_id": participant.id,
                }
            )
        return res
