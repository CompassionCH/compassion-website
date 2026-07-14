##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


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
