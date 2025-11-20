import logging
from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDonationFlow(HttpCase):

    def setUp(self):
        super(TestDonationFlow, self).setUp()
        # 1. Wir erstellen ein Test-Produkt
        self.donation_product = self.env['product.template'].create({
            'name': 'Test Donation Goat',
            'list_price': 50.0,
            'activat assion': True,
            'my_compassion_donation_type': 'gift',
            'website_published': True,
            'my_compassion_donation_quantity_low': 1,
            'my_compassion_donation_quantity_medium': 2,
            'my_compassion_donation_quantity_high': 3,
        })

        # 2. Wir erstellen einen Portal-User
        self.user_portal = self.env['res.users'].create({
            'name': 'Test Donor',
            'login': 'test_donor',
            'password': 'password',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })

    def test_website_donation_flow(self):
        """
        Dieser Test simuliert einen User, der ein Geschenk auswählt,
        in den Warenkorb legt und es dort wieder löscht.
        """
        _logger.info("START: test_website_donation_flow - Browser wird gestartet")

        # 1. UI TEST
        # Wenn die Tour fehlschlägt (JS Error oder Timeout), wirft diese Zeile
        # eine Exception und der Code bricht hier ab.
        self.start_tour(
            "/my2/gift-package/add",
            "donation_tour_full_cycle",
            login="test_donor"
        )

        _logger.info("MITTE: Tour erfolgreich beendet. Prüfe nun Datenbank...")

        # 2. DATENBANK TEST
        partner = self.user_portal.partner_id

        sale_order = self.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft')
        ], order='id desc', limit=1)

        # Wenn diese Assertion fehlschlagen würde, würdest du einen ERROR im Log sehen.
        # Dass der Test grün ist, bedeutet, self.assertTrue war erfolgreich.
        self.assertTrue(sale_order, "Es sollte eine Sale Order (Warenkorb) für den User existieren.")

        # Assertion: Warenkorb muss leer sein
        self.assertFalse(sale_order.order_line, "Der Warenkorb sollte nach dem Löschen im UI auch in der DB leer sein.")

        _logger.info("ENDE: Test erfolgreich! Datenbank-Status ist korrekt.")