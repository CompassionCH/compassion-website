from psycopg2.errors import LockNotAvailable

from odoo import _, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL


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

    def _cart_update(self, *args, **kwargs):
        """Only the gift package's routes add or change the lines of a
        MyCompassion cart (they write the lines themselves). website_sale's
        cart routes would get around its checks: a new quantity prices a
        donation at the product's list price again, and a shop product can
        be priced under the fund minimum."""
        if self.website_id.is_my_compassion:
            raise UserError(
                _("Please add and change your donations in your gift package.")
            )
        return super()._cart_update(*args, **kwargs)

    def _my2_payment_outcome(self, except_transaction=None):
        """What became of the payment of a donation order:

        - "paid": the order is confirmed, or one of its payments may still
          succeed: pending (BLIK in the bank app, 3DS), authorized, a draft
          the provider already has, or a cancelled or refused one whose
          refusal is not certain (_my2_refusal_is_certain, e.g. a payment the
          provider never confirmed nor refused) - the donor is thanked, and
          never asked to pay a second time;
        - "failed": its last payment was cancelled or refused for certain,
          and none may still succeed - the donor gets the cart back to pay
          again;
        - "": it was never paid.

        Drafts are ignored, as website_sale does (get_portal_last_transaction):
        an abandoned newer one hides nothing. except_transaction is left out
        of the payments that may still succeed (the one being checked).
        """
        if not self:
            return ""
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            return "paid"
        transactions = self.transaction_ids
        if except_transaction:
            transactions -= except_transaction
        may_succeed = transactions.filtered(
            lambda t: t.state in ("pending", "authorized", "done")
            or (t.state == "draft" and t.provider_reference)
            or (t.state in ("cancel", "error") and not t._my2_refusal_is_certain())
        )
        if may_succeed:
            return "paid"
        if self.get_portal_last_transaction().state in ("cancel", "error"):
            return "failed"
        return ""

    def _my2_lock_for_new_payment(self, except_transaction=None):
        """Refuse a new payment of this order while an earlier one is paid or
        may still succeed (_my2_payment_outcome): a second tab, or a payment
        waiting in the bank app, would be charged as well.

        Serialized on the order row, which is written (a no-op), not only
        locked: Odoo runs at REPEATABLE READ, where a request that only
        locks the row after a concurrent payment committed still reads its
        snapshot from before that payment. Over a row that payment wrote,
        the lock fails with a serialization error instead, and Odoo replays
        the request against the committed payment. A payment of the order
        still being created holds the row: refused at once, as website_sale
        does. except_transaction is not counted (see _my2_payment_outcome).
        """
        self.ensure_one()
        try:
            self.env.cr.execute(
                SQL(
                    "SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE NOWAIT",
                    self.id,
                )
            )
        except LockNotAvailable:
            raise UserError(_("Payment is already being processed.")) from None
        self.env.cr.execute(
            SQL("UPDATE sale_order SET write_date = write_date WHERE id = %s", self.id)
        )
        if self._my2_payment_outcome(except_transaction) == "paid":
            raise UserError(
                _("This donation is already paid, or its payment is under way.")
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
