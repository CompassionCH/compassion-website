from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDonation(WebsiteSale):
    @route(
        ["/shop/confirm_order"], type="http", auth="public", website=True, sitemap=False
    )
    def shop_confirm_order(self, **post):
        redirection = super().shop_confirm_order(**post)
        order_sudo = request.website.sale_get_order()
        if order_sudo._is_anonymous_cart():
            # If the order is anonymous, we try to match it to an existing partner
            # based on the form values
            partner = (
                request.env["res.partner.match"]
                .sudo()
                .match_values_to_partner(post, match_create=False)
            )
            if partner:
                order_sudo.partner_id = partner[:1].id
        return redirection
