from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestShopHidden(HttpCase):
    def setUp(self):
        super().setUp()
        self.website = self.env["website"].get_current_website()
        self.product = self.env["product.template"].create(
            {"name": "Hidden product", "website_published": True}
        )

    def test_shop_without_redirect_is_not_found(self):
        self.website.shop_redirect_url = False
        response = self.url_open("/shop", allow_redirects=False)
        self.assertEqual(response.status_code, 404)

    def test_shop_redirects_to_configured_page(self):
        self.website.shop_redirect_url = "/contactus"
        response = self.url_open("/shop", allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/contactus"))

    def test_shop_category_pages_redirect_too(self):
        self.website.shop_redirect_url = "/contactus"
        response = self.url_open("/shop/page/2", allow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_product_page_is_not_found(self):
        response = self.url_open(f"/shop/{self.product.id}", allow_redirects=False)
        self.assertEqual(response.status_code, 404)

    def test_redirect_url_must_be_local(self):
        for url in ("https://example.com", "//example.com", "contactus", "/shop"):
            with self.assertRaises(ValidationError):
                self.website.shop_redirect_url = url
