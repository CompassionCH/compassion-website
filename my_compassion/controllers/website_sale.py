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
from odoo.exceptions import ValidationError
from odoo.http import request

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


# Payment attempts of a visitor's cart within an hour: card testers try stolen
# card numbers one after the other on public donation pages.
MAX_VISITOR_PAYMENT_ATTEMPTS = 5


class MyCompassionShopPayment(PaymentPortal):
    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """For a visitor on a MyCompassion website:

        - never a saved card: the cart's partner was created by an email
          anyone may type, and may later be someone's account - their cards
          are theirs. The gift package shows a visitor no saved card; this
          refuses one sent all the same;
        - a few payment attempts per cart and hour only.
        """
        if request.website.is_my_compassion and request.env.user._is_public():
            if kwargs.get("token_id"):
                raise ValidationError(_("Please enter your card details."))
            order = request.env["sale.order"].sudo().browse(order_id).exists()
            recent = order.transaction_ids.filtered(
                lambda t: t.create_date > fields.Datetime.now() - timedelta(hours=1)
            )
            if len(recent) >= MAX_VISITOR_PAYMENT_ATTEMPTS:
                raise ValidationError(
                    _("Too many payment attempts. Please try again later.")
                )
        return super().shop_payment_transaction(order_id, access_token, **kwargs)
