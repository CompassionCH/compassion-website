from urllib.parse import urlencode

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCheckoutPartner(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Donation",
                "type": "service",
                "list_price": 10.0,
                "sale_ok": True,
                "is_published": True,
                "website_id": cls.website.id,
            }
        )
        cls.donor = cls.env["res.partner"].create(
            {"name": "Existing Donor", "email": "existing.donor@example.com"}
        )

    def _visitor_cart(self):
        self.make_jsonrpc_request(
            "/shop/cart/update_json", {"product_id": self.product.id, "add_qty": 1}
        )
        return self.env["sale.order"].search(
            [("website_id", "=", self.website.id)], order="id desc", limit=1
        )

    def test_checkout_never_hands_an_existing_partner_to_a_visitor(self):
        """A visitor's cart keeps its own partner, whatever the values sent to
        the checkout."""
        cart = self._visitor_cart()
        visitor = self.website.user_id.partner_id
        self.assertEqual(cart.partner_id, visitor)
        query = urlencode({"email": self.donor.email, "name": self.donor.name})
        self.url_open(f"/shop/confirm_order?{query}")
        cart.invalidate_recordset()
        self.assertEqual(cart.partner_id, visitor)
