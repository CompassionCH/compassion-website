import logging
import random
from datetime import date
from unittest.mock import patch
from unittest.mock import MagicMock
from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDonationFlow(HttpCase):

    def setUp(self):
        # WICHTIG: super().setUp() muss ZUERST aufgerufen werden,
        # damit 'self.env' initialisiert wird.
        super(TestDonationFlow, self).setUp()

        # ----------------------------------------------------------------------
        # FIX: Authentifizierung patchen (Registry Level)
        # Wir patchen die Methode direkt auf dem aktiven Model im Speicher.
        # Das umgeht das Problem, dass String-Patches bei Odoo oft ignoriert werden.
        # side_effect=None -> Methode tut nichts -> Login erfolgreich.
        # ----------------------------------------------------------------------
        RegistryResUsers = type(self.env['res.users'])
        self.auth_patcher = patch.object(RegistryResUsers, '_check_credentials', side_effect=None)
        self.auth_patcher.start()
        self.addCleanup(self.auth_patcher.stop)

        # Cache leeren
        self.env.cache.invalidate()

        self.run_id = random.randint(1000, 9999)
        image_b64 = b"R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs="

        color = self.env['theme.compassion.colors'].search([], limit=1)
        if not color:
            color = self.env['theme.compassion.colors'].create({
                'name': 'Test Blue',
                'color': '#005596', # Falls das Modell ein Farb-Feld hat (geraten, sonst reicht name)
            })

        pictogram = self.env['theme.compassion.pictograms'].search([], limit=1)
        if not pictogram:
            pictogram = self.env['theme.compassion.pictograms'].create({
                'name': 'Test Heart',
                'class_name': 'fa fa-heart', # Wichtig: Dies wird ins HTML gerendert
            })

        self.donation_product = self.env['product.template'].search([('name', '=', 'Test Donation Goat2')], limit=1)
        if not self.donation_product:
            self.donation_product = self.env['product.template'].create({
                'name': 'Test Donation Goat2',
                'list_price': 50.0,
                'activate_for_my_compassion': True,
                'my_compassion_name': 'Goat Donation Fund',
                'my_compassion_description': 'Support children by donating goats.',
                'my_compassion_donation_type': 'fund',
                'my_compassion_color': color.id,
                'my_compassion_pictogram': pictogram.id,
                'my_compassion_image': image_b64,
                'website_published': True,
                'my_compassion_donation_quantity_low': 1,
                'my_compassion_donation_quantity_medium': 2,
                'my_compassion_donation_quantity_high': 3,
            })

        partner = self.env['res.partner'].create({
            'name': f'Test Donor {self.run_id}',
            'email': f'test.donor.{self.run_id}@example.com',
        })
        self.env['res.partner'].flush()

        self.user_portal = self.env['res.users'].create({
            'login': f'test_donor_{self.run_id}',
            'password': 'password',
            'partner_id': partner.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
        })

        existing_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.user_portal.partner_id.id),
            ('state', '=', 'draft')
        ])
        if existing_orders:
            existing_orders.unlink()

        # Manueller Commit, falls du im Debugger stoppen und in der DB gucken willst:
        self.env.cr.commit()

    def test_website_donation_flow(self):
        _logger.info(f"START: Test Run")

        self.start_tour(
            "/my2/gift-package/add",
            "donation_tour_full_cycle",
            login=self.user_portal.login
        )

        partner = self.user_portal.partner_id
        sale_order = self.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft')
        ], order='id desc', limit=1)

        self.assertTrue(sale_order, "FEHLER: Keine Sale Order gefunden.")
        self.assertFalse(sale_order.order_line, "Warenkorb sollte leer sein.")