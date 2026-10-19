from odoo import _, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _send_order_notification_mail(self, mail_template):
        """No Odoo sales email for a MyCompassion donation.

        Paying online confirms the order, and sale then emails the donor an
        order confirmation (or a "payment pending/executed" notice) - a
        webshop email about an "order", in the partner's language or not,
        on top of Compassion's own thanks and donation receipts. The other
        websites (crowdfunding, events...) keep the standard behaviour.
        """
        if self.website_id.is_my_compassion:
            return None
        return super()._send_order_notification_mail(mail_template)

    def _get_update_prices_lines(self):
        """The donor chose the amounts of a MyCompassion cart: they are never
        reset to the product's price, e.g. when a visitor logs in and the cart
        moves to an account with another pricelist or fiscal position."""
        lines = super()._get_update_prices_lines()
        return lines.filtered(
            lambda line: not line.order_id.website_id.is_my_compassion
        )

    def _check_cart_is_ready_to_be_paid(self):
        self._check_gift_limits()
        return super()._check_cart_is_ready_to_be_paid()

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
