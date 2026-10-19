##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, http
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


class MyCompassionShopPayment(PaymentPortal):
    @http.route()
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """A visitor never pays with a saved card: the cart's partner was
        created by an email anyone may type, and may later be someone's
        account - their cards are theirs. The gift package shows a visitor no
        saved card; this refuses one sent all the same."""
        if (
            request.website.is_my_compassion
            and request.env.user._is_public()
            and kwargs.get("token_id")
        ):
            raise ValidationError(_("Please enter your card details."))
        return super().shop_payment_transaction(order_id, access_token, **kwargs)
