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

    cart_link = fields.Char(
        compute="_compute_cart_link",
        help="What link to redirect when clicking on the order line from the cart",
    )
    is_anonymous = fields.Boolean(
        help="Should the donation be anonymous?", default=False
    )
    opt_out = fields.Boolean(
        help="Should the donor opt out of marketing?", default=False
    )

    def _compute_cart_link(self):
        # Can be overriden to display a custom link
        for line in self:
            line.cart_link = line.product_id.website_url

    def get_donation_description(self, product):
        """Get the description for a donation."""
        self.ensure_one()
        return _("Donation for %s") % product.name

    def get_sale_order_line_multiline_description_sale(self, product):
        """We override this method because we want a custom description when a
        sale order is connected with a donation.
        """
        if self.order_id.is_donation:
            return self.get_donation_description(product)
        else:
            return super().get_sale_order_line_multiline_description_sale(product)

    @api.depends("order_id.is_donation", "product_id.display_name")
    def _compute_name_short(self):
        """We override this method because we want a custom description when a
        sale order is connected with an ambassador or event.
        """
        for line in self:
            if line.order_id.is_donation:
                line.name_short = line.get_donation_description(line.product_id)
            else:
                line.name_short = super(SaleOrderLine, line)._compute_name_short()

    def _prepare_invoice_line(self, **optional_values):
        # Propagate anonymous to move_line
        optional_values["is_anonymous"] = self.is_anonymous
        return super()._prepare_invoice_line(**optional_values)
