from odoo import Command
from odoo.tests import TransactionCase, tagged

from ..controllers.my2_sponsorships import _product_display_price


@tagged("post_install", "-at_install")
class TestWizardPrices(TransactionCase):
    """The amounts of the sponsorship wizard copy come from the website's
    pricelist, like the contract lines, not from the list price of a
    product shared by every country company."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.ref("base.PLN")
        cls.currency.active = True
        cls.company = cls.env["res.company"].create(
            {"name": "Wizard Prices Co", "currency_id": cls.currency.id}
        )
        cls.website = cls.env["website"].create(
            {"name": "Wizard Prices", "company_id": cls.company.id}
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Wizard Prices Sponsorship",
                "default_code": "wizard_prices_test",
                "list_price": 42.0,
            }
        )

    def _pricelist(self, price):
        return self.env["product.pricelist"].create(
            {
                "name": "Wizard Prices PLN",
                "currency_id": self.currency.id,
                "company_id": self.company.id,
                "website_id": self.website.id,
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": self.product.id,
                            "compute_price": "fixed",
                            "fixed_price": price,
                        }
                    )
                ],
            }
        )

    def test_amount_comes_from_the_website_pricelist(self):
        self._pricelist(140.0)
        self.website.invalidate_recordset(["pricelist_id", "currency_id"])
        self.assertEqual(
            _product_display_price("wizard_prices_test", self.website), "140"
        )
        self.assertEqual(self.website.currency_id, self.currency)

    def test_unknown_product_shows_no_amount(self):
        self.assertEqual(_product_display_price("no_such_code", self.website), "")
