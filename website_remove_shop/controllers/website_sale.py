from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDonation(WebsiteSale):
    @http.route(
        [
            "/shop",
            "/shop/page/<int:page>",
            '/shop/category/<model("product.public.category"):category>',
            '/shop/category/<model("product.public.category"):category>/page/<int:page>',
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def shop(self, page=0, category=None, search="", **post):
        redirect_url = request.website.shop_redirect_url
        if not redirect_url:
            raise request.not_found()
        return request.redirect(request.env["ir.http"]._url_for(redirect_url), code=302)

    @http.route(
        ['/shop/<model("product.template"):product>'],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def product(self, product, category="", search="", **kwargs):
        raise request.not_found()
