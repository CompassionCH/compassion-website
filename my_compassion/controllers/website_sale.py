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
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.payment import PaymentPortal


class MyCompassionWebsiteSale(WebsiteSale):
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

        - for a visitor, never a saved card: the order's partner was created
          from an email anyone may type, and may later be someone's account -
          their cards are theirs. The gift package shows a visitor no saved
          card; this refuses one sent all the same;
        - for a visitor, a few payment attempts per order and hour only.
        """
        if not request.env.user._is_public():
            return
        if token_id:
            raise ValidationError(_("Please enter your card details."))
        recent = order_sudo.transaction_ids.filtered(
            lambda t: t.create_date > fields.Datetime.now() - timedelta(hours=1)
        )
        if len(recent) >= MAX_VISITOR_PAYMENT_ATTEMPTS:
            raise ValidationError(
                _("Too many payment attempts. Please try again later.")
            )
