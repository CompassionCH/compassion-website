##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from datetime import timedelta

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request

from odoo.addons.sale.controllers.portal import PaymentPortal as SalePaymentPortal
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.controllers.payment import PaymentPortal


class MyCompassionWebsiteSale(Delivery):
    @http.route()
    def shop_payment_confirmation(self, **post):
        """On a MyCompassion portal website, send the donor to the branded
        thank-you page instead of the sales order summary. The gift/donation
        flow is the only path that reaches this route on such a website.
        """
        if request.website.is_my_compassion:
            return request.redirect("/my2/gifts/thankyou")
        return super().shop_payment_confirmation(**post)

    def _check_cart(self, order_sudo):
        """A MyCompassion cart is paid on the gift package only, never through
        the standard checkout (/shop/checkout, /shop/address and its submit,
        /shop/confirm_order, /shop/payment): its address form edits the
        cart's partner, which for a visitor is a donor created from an email
        anyone may type. Decided on the cart's website: a session can reach
        /shop on another website of the same domain."""
        if order_sudo.website_id.is_my_compassion:
            return request.redirect("/my2/gift-package")
        return super()._check_cart(order_sudo)

    @http.route()
    def cart(self, access_token=None, revive="", **post):
        """The gift package is the cart page of a MyCompassion cart: website_sale's
        one would offer an express payment form with the cart's access token."""
        if request.website.sale_get_order().website_id.is_my_compassion:
            return request.redirect("/my2/gift-package")
        return super().cart(access_token=access_token, revive=revive, **post)

    @http.route()
    def process_express_checkout(self, billing_address, **kwargs):
        """No express checkout for a MyCompassion cart: it sets the cart's
        partners without the email step."""
        self._my2_refuse_express_checkout()
        return super().process_express_checkout(billing_address, **kwargs)

    @http.route()
    def express_checkout_process_delivery_address(self, partial_delivery_address):
        """No express checkout for a MyCompassion cart: it creates the cart's
        partner without the email step."""
        self._my2_refuse_express_checkout()
        return super().express_checkout_process_delivery_address(
            partial_delivery_address
        )

    def _my2_refuse_express_checkout(self):
        if request.website.sale_get_order().website_id.is_my_compassion:
            raise ValidationError(_("Please pay your donation from your gift package."))


# Payment attempts of a visitor's cart within an hour: card testers try stolen
# card numbers one after the other on public donation pages.
MAX_VISITOR_PAYMENT_ATTEMPTS = 5


class MyCompassionShopPayment(PaymentPortal, SalePaymentPortal):
    """The payment routes of a MyCompassion order, decided on the order's
    website: its access token works on any host, and a route outside /my2
    resolves to the website of the domain."""

    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """The gift package's payment route (see _my2_check_new_payment)."""
        order_sudo = self._my2_order(order_id, access_token)
        if order_sudo.website_id.is_my_compassion:
            self._my2_check_new_payment(order_sudo, **kwargs)
        return super().shop_payment_transaction(order_id, access_token, **kwargs)

    @http.route()
    def portal_order_transaction(self, order_id, access_token, **kwargs):
        """sale's payment route, which takes any amount: the gift package
        never uses it, so a visitor may not pay a MyCompassion order here."""
        order_sudo = self._my2_order(order_id, access_token)
        if order_sudo.website_id.is_my_compassion:
            if request.env.user._is_public():
                raise ValidationError(
                    _("Please pay your donation from your gift package.")
                )
            self._my2_check_new_payment(order_sudo, **kwargs)
        return super().portal_order_transaction(order_id, access_token, **kwargs)

    def _my2_order(self, order_id, access_token):
        """The order a payment route is called for, or an empty recordset
        when the access check fails (the route itself then refuses it)."""
        try:
            return self._document_check_access("sale.order", order_id, access_token)
        except (AccessError, MissingError):
            return request.env["sale.order"].sudo()

    def _my2_check_new_payment(self, order_sudo, token_id=None, **kwargs):
        """Before a new payment of a MyCompassion order:

        - none while an earlier one is paid or may still succeed (a second
          tab, a payment waiting in the bank app): both could be charged
          (sale.order._my2_lock_for_new_payment, which also serializes
          concurrent requests);
        - for a visitor, only for the donor their session gave at the email
          step: not before it, nor from another session holding the order's
          access token;
        - a saved card of the user's own (commercial) partner only - never one
          for a visitor: the order's partner was created from an email anyone
          may type, and may later be someone's account - their cards are
          theirs. The gift package shows a visitor no saved card; this refuses
          one sent all the same;
        - for a visitor, a few payment attempts per order and hour only, and
          a few per client IP on the website, all carts and sessions together
          (my2.payment.attempt.counter).
        """
        order_sudo._my2_lock_for_new_payment()
        if token_id:
            token = request.env["payment.token"].sudo().browse(int(token_id)).exists()
            owner = token.partner_id.commercial_partner_id
            if (
                request.env.user._is_public()
                or owner != request.env.user.partner_id.commercial_partner_id
            ):
                raise ValidationError(_("Please enter your card details."))
        if not request.env.user._is_public():
            return
        if request.session.get("my2_donor_partner_id") != order_sudo.partner_id.id:
            raise ValidationError(_("Please give your email before paying."))
        recent = order_sudo.transaction_ids.filtered(
            lambda t: t.create_date > fields.Datetime.now() - timedelta(hours=1)
        )
        counter = request.env["my2.payment.attempt.counter"].sudo()
        if len(recent) >= MAX_VISITOR_PAYMENT_ATTEMPTS or not (
            counter._my2_count_attempt(order_sudo, request.httprequest.remote_addr)
        ):
            raise ValidationError(
                _("Too many payment attempts. Please try again later.")
            )
