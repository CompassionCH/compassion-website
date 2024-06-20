##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, fields, models


class SaleOrderLine(models.Model):
    """Add salespersons to invoice_lines."""

    _inherit = "sale.order.line"

    registration_id = fields.Many2one("event.registration")

    def _compute_cart_link(self):
        for line in self:
            if line.registration_id:
                line.cart_link = line.registration_id.website_url
            else:
                super(SaleOrderLine, line)._compute_cart_link()

    def get_donation_description(self, product):
        """Get the description for a donation."""
        if self.registration_id:
            return _("Donation for %s") % self.registration_id.partner_id.preferred_name
        return super().get_donation_description(product)

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        registration = getattr(self, "registration_id", False)
        analytic_id = registration.compassion_event_id.analytic_id.id
        if registration:
            res.update(
                {
                    "user_id": registration.partner_id.id,
                    "analytic_account_id": analytic_id,
                }
            )
        return res
