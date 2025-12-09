import logging
from sys import dont_write_bytecode
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase, ChromeBrowser

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDonationFlow(HttpCase):
    TEST_DOMAIN = "http://127.0.0.1:8069"

    def setUp(self):
        super(TestDonationFlow, self).setUp()

        # Execute setup steps
        self._setup_website()
        self._patch_authentication()
        self._patch_browser()

    def _setup_website(self):
        """
        Configures the website environment:
        - Selects the target website (MyCompassion).
        - Forces the environment context to the target website.
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

    def test_donation_tour(self):
        _logger.info("START TEST RUN: Donation Tour")

        start_url = f"{self.TEST_DOMAIN}/my2/dashboard"
        tour_name = "donation_tour_full_cycle"
        self.browser_js(
            url_path=start_url,
            code=f"odoo.__DEBUG__.services['web_tour.tour'].run('{tour_name}')",
            ready=f"odoo.__DEBUG__.services['web_tour.tour'].tours.{tour_name}.ready",
            login="admin",
            timeout=180,
        )