from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDonation(WebsiteSale):
    def sitemap_shop(self, env, rule, qs):
        return {}

    @http.route(
        ['/shop/<model("product.template"):product>'],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def product(self, product, category="", search="", **kwargs):
        return super().product(product, category, search, **kwargs)

    @http.route(
        ["/shop/terms"], type="http", auth="public", website=True, sitemap=False
    )
    def terms(self, **kw):
        return super().terms(**kw)
