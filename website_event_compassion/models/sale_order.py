##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_update(
        self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs
    ):
        """Don't update lines linked to an event participant, because they are
        donations and the amount is fixed by the user.
        """
        if line_id:
            line = self.env["sale.order.line"].browse(line_id)
            if line.registration_id:
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
