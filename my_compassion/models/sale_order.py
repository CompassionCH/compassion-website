from odoo import _, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_payment_transaction(self, vals):
        self._check_gift_limits()
        return super()._create_payment_transaction(vals)

    def _check_gift_limits(self):
        """The donation form checks the gift limits when a line is added, but an
        abandoned cart can become the current one again later (sale_get_order
        falls back to the partner's last draft order), so a cart that was filled
        while another one was still unpaid must be re-checked here (T3451).
        """
        for order in self:
            for line in order.order_line.filtered("is_gift"):
                limits = line.product_template_id.get_donation_limits(
                    order.company_id,
                    order.partner_id,
                    line.gift_recipient_id.id,
                    order,
                )
                if limits.get("remaining_donations", 0) < 0:
                    child = line.gift_recipient_id.child_id
                    raise ValidationError(
                        _(
                            "You've already reached the yearly limit of "
                            "%(gift)s for %(child)s. Please remove it from your "
                            "gift basket before paying."
                        )
                        % {
                            "gift": line.product_template_id.name,
                            "child": child.preferred_name
                            or line.gift_recipient_id.display_name,
                        }
                    )
