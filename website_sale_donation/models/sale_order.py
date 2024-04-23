##############################################################################
#
#    Copyright (C) 2024 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_donation = fields.Boolean()

    def add_donation(self, product_id, price_unit, qty=1, **other_line_vals):
        """Convert the sale order to a donation."""
        self.ensure_one()
        self.write({"is_donation": True})
        order_line_id = self._cart_update(
            product_id=product_id,
            set_qty=qty,
        )["line_id"]
        order_line = self.env["sale.order.line"].browse(order_line_id)
        line_vals = {
            "price_unit": price_unit,
            "product_uom_qty": qty,
        }
        if other_line_vals:
            line_vals.update(other_line_vals)
        order_line.write(line_vals)
        # We automatically validate the order
        self.workflow_process_id = self.env.ref(
            "sale_automatic_workflow.automatic_validation"
        )
        return True

    def _cart_update(
        self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs
    ):
        """Don't update lines when it's a donation,
        because the amount is fixed by the user.
        """
        if line_id:
            line = self.env["sale.order.line"].browse(line_id)
            if line.order_id.is_donation:
                if set_qty == 0 and add_qty is None:
                    # In this case, we want to remove the line (called from cart)
                    return super()._cart_update(
                        product_id, line_id, add_qty, set_qty, **kwargs
                    )
                if set_qty:
                    line.write(
                        {"product_uom_qty": set_qty, "price_unit": line.price_unit}
                    )
                return {"quantity": line.product_uom_qty}
        return super()._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

    def _create_invoices(self, grouped=False, final=False, date=None):
        # Opt out partners if desired
        for line in self.order_line.filtered("opt_out"):
            self.env["mailing.contact.subscription"].sudo().search(
                [("contact_id.email", "=", line.order_partner_id.email)]
            ).write({"opt_out": True})
        return super()._create_invoices(grouped, final, date)
