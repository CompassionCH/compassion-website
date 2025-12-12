import logging
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase, ChromeBrowser

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDonationFlow(HttpCase):

    TEST_DOMAIN = "http://127.0.0.1:8069"
    CUSTOM_AMOUNT_TEST = 75
    MOCK_TEST_DATA = {
        'product_name': 'Test Product',
        'price': 50.0,
        'description': 'This is a test product for donation flow testing.',
        'amounts': {
            'low': 1,
            'medium': 2,
            'high': 3
        }
    }

    def setUp(self):
        super(TestDonationFlow, self).setUp()

        # Execute setup steps
        self._setup_website()
        self._patch_authentication()
        self._patch_browser()
        self._setup_test_data()

    def _setup_website(self):
        """
        Configures the website environment:
        - Selects the target website (MyCompassion).
        - Forces the environment context to the target website.
        - Only persists for the duration of the test run.
        """
        _logger.info("SETUP (WEBSITE): Configuring MyCompassion as target website for the environment.")

        target_website = self.env['website'].sudo().search([('name', '=', 'MyCompassion')], limit=1)

        if not target_website:
            raise AssertionError("FATAL: Target website (MyCompassion) not found!")

        # Must be localhost so that authentication cookies are accepted
        target_website.write({'domain': self.TEST_DOMAIN})

        # Force environment context to this website
        self.env = self.env(context={'website_id': target_website.id})

    def _patch_authentication(self):
        """
        Patches res.users to bypass credential checks during the test.
        """
        _logger.info("SETUP (AUTH): Patching res.users to bypass authentication checks.")

        RegistryResUsers = type(self.env['res.users'])
        self.auth_patcher = patch.object(RegistryResUsers, '_check_credentials', side_effect=None)
        self.auth_patcher.start()
        self.addCleanup(self.auth_patcher.stop)

    def _patch_browser(self):
        """
        Patches the Chrome browser spawn process.
        Stores the original method and replaces it with our custom handler.
        """

        _logger.info("SETUP (BROWSER): Patching Chrome browser spawn process.")

        self.original_chrome_spawn = ChromeBrowser._spawn_chrome

        self.browser_patcher = patch.object(
            ChromeBrowser,
            '_spawn_chrome',
            side_effect=self._custom_chrome_spawn_handler,
            autospec=True,
        )
        self.browser_patcher.start()
        self.addCleanup(self.browser_patcher.stop)

        _logger.info("Patched Chrome browser spawn method.")

    def _custom_chrome_spawn_handler(self, browser_instance, cmd):
        """
        Callback that modifies the Chrome command line arguments.
        :param browser_instance: The instance of ChromeBrowser (internally used by Odoo)
        :param cmd: The list of command line arguments
        """
        new_args = [
            '--headless=new',
            '--disable-component-extensions-with-background-pages',
            '--window-size=1920,1080',
        ]

        for arg in new_args:
            if arg not in cmd:
                cmd.append(arg)

        return self.original_chrome_spawn(browser_instance, cmd)


    def _setup_test_data(self):
        """
        Sets up transient test data required for the donation flow.
        Ensures the cart is empty and creates a donation product.
        """
        _logger.info("SETUP (DATA): Clearing existing carts for admin user.")
        admin_partner = self.env.ref('base.user_admin').partner_id

        existing_orders = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner.id),
            ('state', 'in', ['draft', 'sent']),
        ])

        if existing_orders:
            existing_orders.action_cancel()
            existing_orders.unlink()

        _logger.info("SETUP (DATA): Creating donation product for testing.")

        image_b64 = b"R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs="

        color = self.env['theme.compassion.colors'].search([], limit=1)
        if not color:
            raise AssertionError("FATAL: theme.compassion.colors is not present!")


        pictogram = self.env['theme.compassion.pictograms'].search([], limit=1)
        if not pictogram:
            raise AssertionError("FATAL: theme.compassion.pictograms is not present!")

        self.donation_product = self.env['product.template'].create({
            'name': self.MOCK_TEST_DATA['product_name'],
            'list_price': self.MOCK_TEST_DATA['price'],
            'activate_for_my_compassion': True,
            'my_compassion_name': self.MOCK_TEST_DATA['product_name'],
            'my_compassion_description': self.MOCK_TEST_DATA['description'],
            'my_compassion_donation_type': 'fund',
            'my_compassion_color': color.id,
            'my_compassion_pictogram': pictogram.id,
            'my_compassion_image': image_b64,
            'website_published': True,
            'my_compassion_donation_quantity_low': self.MOCK_TEST_DATA['amounts']['low'],
            'my_compassion_donation_quantity_medium': self.MOCK_TEST_DATA['amounts']['medium'],
            'my_compassion_donation_quantity_high': self.MOCK_TEST_DATA['amounts']['high'],
        })

    # ---------------------------------------------------------
    # TESTS
    # ---------------------------------------------------------

    def test_single_one_time_fund_with_suggested_amount(self):
        _logger.info("START TEST: single_one_time_fund_with_suggested_amount")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_with_suggested_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'], "ERROR: The total amount of the order does not match the expected price.")

    def test_single_one_time_fund_with_custom_amount(self):
        _logger.info("START TEST: single_one_time_fund_with_custom_amount")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_with_custom_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.CUSTOM_AMOUNT_TEST,"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.CUSTOM_AMOUNT_TEST, "ERROR: The total amount of the order does not match the expected price.")

    def test_single_monthly_fund_with_suggested_amount(self):
        _logger.info("START TEST: single_monthly_fund_with_suggested_amount")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_monthly_fund_with_suggested_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'monthly', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'], "ERROR: The total amount of the order does not match the expected price.")


    def test_single_monthly_fund_with_custom_amount(self):
        _logger.info("START TEST: single_monthly_fund_with_custom_amount")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_monthly_fund_with_custom_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.CUSTOM_AMOUNT_TEST,"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'monthly', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.CUSTOM_AMOUNT_TEST, "ERROR: The total amount of the order does not match the expected price.")


    def test_add_several_funds(self):
        _logger.info("START TEST: test_full_flow_add_and_remove_item")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_with_suggested_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        tour_name = "single_monthly_fund_with_custom_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )
        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 2, "ERROR: Should be exactly one current draft order.")

        first_product = target_line[0]
        second_product = target_line[1]

        self.assertEqual(first_product.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(first_product.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(first_product.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")

        self.assertEqual(second_product.price_unit, self.CUSTOM_AMOUNT_TEST,"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(second_product.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(second_product.frequency, 'monthly', "ERROR: The frequency of the order line is not set to one_time.")

        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'] + self.CUSTOM_AMOUNT_TEST, "ERROR: The total amount of the order does not match the expected price.")

    def test_full_flow_add_and_remove_item(self):
        _logger.info("START TEST: test_full_flow_add_and_remove_item")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_with_suggested_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'], "ERROR: The total amount of the order does not match the expected price.")

        tour_name = "remove_item_from_cart"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertEqual(current_order.cart_quantity, 0, "ERROR: Should be empty current draft order.")
        self.assertEqual(target_line.price_unit, 0,"ERROR: The price per unit must be zero after removal.")
        self.assertEqual(current_order.amount_total, 0, "ERROR: The total amount of the order must be zero after removal.")

    def test_full_flow_add_and_edit_item(self):
        _logger.info("START TEST: test_full_flow_add_and_edit_item_in_cart")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_with_suggested_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'], "ERROR: The total amount of the order does not match the expected price.")


        tour_name = "update_item_in_cart"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.CUSTOM_AMOUNT_TEST,"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.CUSTOM_AMOUNT_TEST, "ERROR: The total amount of the order does not match the expected price.")

    def test_single_one_time_fund_through_modal(self):
        _logger.info("START TEST: single_one_time_fund_through_modal")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "single_one_time_fund_through_modal"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id
        # Fetch the current draft sale order for the admin partner
        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = current_order.order_line.filtered(
            lambda line: line.product_id.product_tmpl_id == self.donation_product
        )

        self.assertTrue(current_order, "ERROR: No current draft order found for the admin partner.")
        self.assertEqual(current_order.cart_quantity, 1, "ERROR: Should be exactly one current draft order.")
        self.assertEqual(target_line.price_unit, self.MOCK_TEST_DATA['price'],"ERROR: The price of the order line does not match the expected price.")
        self.assertEqual(target_line.product_uom_qty, 1.0, "ERROR: Amount should be 1.")
        self.assertEqual(target_line.frequency, 'one_time', "ERROR: The frequency of the order line is not set to one_time.")
        self.assertEqual(current_order.amount_total, self.MOCK_TEST_DATA['price'], "ERROR: The total amount of the order does not match the expected price.")

    def test_try_to_submit_empty_custom_amount(self):
        _logger.info("START TEST: try_to_submit_empty_custom_amount")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "try_to_submit_empty_custom_amount"

        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )

        # ---------------------------------------------------------
        # CHECK RESULTS IN DATABASE
        # ---------------------------------------------------------
        admin_partner_id = self.env.ref('base.user_admin').partner_id.id

        current_order = self.env['sale.order'].search([
            ('partner_id', '=', admin_partner_id),
            ('state', '=', 'draft'),
        ], order='id desc', limit=1)
        # Filter order lines to find the one with our test donation product
        target_line = False
        if current_order:
            target_line = current_order.order_line.filtered(
                lambda line: line.product_id.product_tmpl_id == self.donation_product
            )

        self.assertFalse(target_line, "ERROR: Product should NOT be in the cart if validation fails.")
