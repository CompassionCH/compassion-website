import logging
import random
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase, ChromeBrowser

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDonationFlow(HttpCase):
    @classmethod
    def setUpClass(cls):
        # benutzt cls.host intern
        super(TestDonationFlow, cls).setUpClass()

    def setUp(self):
        super(TestDonationFlow, self).setUp()

        # ==========================================================================
        # 2. WEBSITE SELECTION (STRIKT)
        # ==========================================================================
        # Wir suchen die Website, auf der der Test laufen SOLL.
        # Passe 'MyCompassion' an den exakten Namen deiner Website in Odoo an.
        target_website = self.env['website'].sudo().search([('name', 'ilike', 'MyCompassion')], limit=1)

        if not target_website:
            raise AssertionError(f"FATAL: Target website (MyCompassion) not found!")

        _logger.info(f"### TESTING ON WEBSITE: {target_website.name} (ID: {target_website.id}) ###")

        # Anderen Websites eine Fake-Domain geben, damit Odoo sie auf 127.0.0.1 ignoriert
        other_websites = self.env['website'].sudo().search([('id', '!=', target_website.id)])
        if other_websites:
            other_websites.write({'domain': 'ignore.localhost.test'})

       # must be localhost so that authentication cookies are accepted
        target_website.write({'domain': 'http://127.0.0.1:8069/'})

        # Environment auf diese Website zwingen
        self.env = self.env(context={'website_id': target_website.id})

        # ------------------------------------------------------------------
        # Authentifizierung
        # ------------------------------------------------------------------
        RegistryResUsers = type(self.env['res.users'])
        self.auth_patcher = patch.object(RegistryResUsers, '_check_credentials', side_effect=None)
        self.auth_patcher.start()
        self.addCleanup(self.auth_patcher.stop)

        # ------------------------------------------------------------------
        # FIX 2: Chrome Patch
        # ------------------------------------------------------------------
        original_spawn = ChromeBrowser._spawn_chrome

        def patched_spawn(browser_self, cmd):
            _logger.info("### CHROME PATCH APPLIED ###")

            new_args = [
                '--headless=new',  # New headless architecture (required for modern Chrome)
                '--disable-component-extensions-with-background-pages',  # Disable default extensions of browser
                '--window-size=1920,1080',  # Important for stable viewport
            ]

            for arg in new_args:
                if arg not in cmd:
                    cmd.append(arg)

            return original_spawn(browser_self, cmd)

        self.browser_patcher = patch.object(
            ChromeBrowser,
            '_spawn_chrome',
            side_effect=patched_spawn,
            autospec=True,
        )
        self.browser_patcher.start()
        self.addCleanup(self.browser_patcher.stop)

    def test_donation_tour(self):
        _logger.info("START: Donation Tour")

        start_url = "http://127.0.0.1:8069/my2/dashboard"
        self.browser_js(
            url_path=start_url,
            code="odoo.__DEBUG__.services['web_tour.tour'].run('donation_tour_full_cycle_2')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.donation_tour_full_cycle_2.ready",
            login="admin",
            timeout=180,
        )
