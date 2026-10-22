from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDonationProductCompany(TransactionCase):
    """Funds and gifts are shared products: each company publishes them on its
    own MyCompassion website, with its own amounts, in its own currency."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        pln = cls.env.ref("base.PLN")
        pln.active = True
        cls.company_b = cls.env["res.company"].create(
            {"name": "Donation Company B", "currency_id": pln.id}
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Shared Test Fund",
                "type": "service",
                "my_compassion_donation_type": "fund",
                "company_id": False,
            }
        )

    def _settings(self, company):
        product = self.product.with_company(company)
        return (
            product.activate_for_my_compassion,
            product.my_compassion_donation_amount_low,
            product.my_compassion_donation_amount_medium,
            product.my_compassion_donation_amount_high,
        )

    def test_every_company_starts_from_the_same_suggestions(self):
        for company in (self.company_a, self.company_b):
            self.assertEqual(self._settings(company), (False, 15.0, 50.0, 100.0))

    def test_each_company_has_its_own_settings(self):
        self.product.with_company(self.company_a).write(
            {
                "activate_for_my_compassion": True,
                "my_compassion_donation_amount_low": 25.0,
                "my_compassion_donation_amount_medium": 50.0,
                "my_compassion_donation_amount_high": 100.0,
            }
        )
        # The other company does not publish it, and keeps the defaults.
        self.assertEqual(self._settings(self.company_b), (False, 15.0, 50.0, 100.0))

        self.product.with_company(self.company_b).write(
            {
                "activate_for_my_compassion": True,
                "my_compassion_donation_amount_low": 80.0,
                "my_compassion_donation_amount_medium": 200.0,
                "my_compassion_donation_amount_high": 400.0,
            }
        )
        self.assertEqual(self._settings(self.company_b), (True, 80.0, 200.0, 400.0))
        # Back to the first company: its settings are untouched.
        self.assertEqual(self._settings(self.company_a), (True, 25.0, 50.0, 100.0))

        self.product.with_company(self.company_a).activate_for_my_compassion = False
        self.assertFalse(self._settings(self.company_a)[0])
        self.assertTrue(self._settings(self.company_b)[0])

    def test_amounts_in_the_currency_of_the_company(self):
        self.assertEqual(
            self.product.with_company(self.company_a).my_compassion_currency_id,
            self.company_a.currency_id,
        )
        self.assertEqual(
            self.product.with_company(self.company_b).my_compassion_currency_id,
            self.company_b.currency_id,
        )
