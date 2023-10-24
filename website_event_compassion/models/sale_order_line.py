##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    """Add salespersons to invoice_lines."""

    _inherit = "sale.order.line"

    registration_id = fields.Many2one("event.registration")

    def get_sale_order_line_multiline_description_sale(self, product):
        """We override this method because we want a custom description when a
        sale order is connected with an ambassador or event.
        """
        if self.registration_id:
            return _("Donation for %s") % self.registration_id.partner_id.preferred_name
        else:
            return super().get_sale_order_line_multiline_description_sale(product)

    @api.depends("registration_id")
    def _compute_name_short(self):
        """We override this method because we want a custom description when a
        sale order is connected with an ambassador or event.
        """
        for line in self:
            if line.registration_id:
                line.name_short = line.get_sale_order_line_multiline_description_sale(
                    line.product_id
                )
            else:
                line.name_short = super(SaleOrderLine, line)._compute_name_short()

    def _prepare_invoice_line(self, **optional_values):
        # Propagate ambassador and event to invoice line
        res = super()._prepare_invoice_line(**optional_values)
        analytic = self.registration_id.compassion_event_id.analytic_id
        res.update(
            {
                "user_id": self.registration_id.partner_id.id,
                "analytic_account_id": analytic.id,
            }
        )
        return res
