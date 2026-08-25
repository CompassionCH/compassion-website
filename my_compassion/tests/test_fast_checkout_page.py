from odoo.tests import tagged

from odoo.addons.website.tools import MockRequest

from ..controllers.my2_sponsorships import MyCompassionNewSponsorshipController
from ..models.my2_new_sponsorship_wizard import FAST_CHECKOUT_STEP
from .common import DigitalSeamCase

PAYMENT_STEP = "my_compassion.new_sponsorship_wizard_step_payment_methods"
WAP_STEP = "my_compassion.new_sponsorship_wizard_step_wap_options"


@tagged("post_install", "-at_install")
class TestFastCheckoutOnePage(DigitalSeamCase):
    """The one page of the public checkout: e-mail, consent and one button per
    payment mode, which is also what submits it.

    What used to be two steps (identify yourself, then pick a payment method
    from a dropdown) is a single step, so most of what is checked here is that
    nothing else counted on there being a second one.
    """

    def setUp(self):
        super().setUp()
        self.child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(self.child, "the database needs a child")
        self.website_company = self.env["res.company"].create({"name": "One Page Co"})
        provider = self.env["payment.provider"].create(
            {
                "name": "One Page Provider",
                "code": "none",
                "company_id": self.website_company.id,
                "state": "test",
            }
        )
        # the two shapes a mode comes in: charged online right after the
        # click, or collected by the bank later on (CH's eBill, permanent
        # order, direct debit)
        self.digital_mode = self._make_mode("One Page Card", provider=provider)
        self.bank_mode = self._make_mode("One Page Bank Transfer")
        self.unpublished_mode = self._make_mode("One Page Draft", published=False)
        self.foreign_mode = self._make_mode(
            "One Page Other Country",
            company=self.env["res.company"].create({"name": "One Page Other Co"}),
        )

    def _make_mode(self, name, provider=None, published=True, company=None):
        return self.env["account.payment.mode"].create(
            {
                "name": name,
                "company_id": (company or self.website_company).id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": provider.id if provider else False,
                "is_published": published,
            }
        )

    def _wizard(self, sponsorship_type="standard", public=True, **values):
        user = self.env.ref("base.public_user") if public else self.env.user
        return self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": sponsorship_type,
                "user_id": user.id,
                "child_id": self.child.id,
                "company_id": self.website_company.id,
                **values,
            }
        )

    def _render(self, wizard):
        # the MyCompassion website: the theme's form and button components
        # are only instantiated for the website the theme is applied to
        website = self.env.ref("my_compassion.my2_website")
        with MockRequest(self.env, website=website):
            return str(
                MyCompassionNewSponsorshipController._render_form_content(wizard)
            )

    # === The step list ===

    def test_public_standard_checkout_is_one_page(self):
        wizard_model = self.env["new.sponsorship.wizard"]
        self.assertEqual(
            wizard_model._get_step_xmlids("standard", True), [FAST_CHECKOUT_STEP]
        )
        wizard = self._wizard()
        self.assertEqual(wizard.n_steps, 1)
        self.assertEqual(wizard.current_step, self.env.ref(FAST_CHECKOUT_STEP))
        self.assertFalse(wizard.is_done)

    def test_logged_in_flow_keeps_its_payment_step(self):
        # a logged-in sponsor is already identified: nothing to merge, and
        # the dropdown of that step is the DOM contract the Switzerland eBill
        # extension is built on
        wizard_model = self.env["new.sponsorship.wizard"]
        self.assertEqual(
            wizard_model._get_step_xmlids("standard", False), [PAYMENT_STEP]
        )
        wizard = self._wizard(public=False)
        self.assertEqual(wizard.current_step, self.env.ref(PAYMENT_STEP))
        self.assertFalse(wizard._get_payment_mode_buttons())

    def test_write_and_pray_keeps_its_own_options_step(self):
        # Write&Pray takes no payment, so its page has no mode button and
        # the flow keeps a second step - the one asking for the birthdate the
        # age gate in sponsorship_wizard_submit compares
        wizard_model = self.env["new.sponsorship.wizard"]
        self.assertEqual(
            wizard_model._get_step_xmlids("write_and_pray", True),
            [FAST_CHECKOUT_STEP, WAP_STEP],
        )
        wizard = self._wizard(sponsorship_type="write_and_pray")
        self.assertEqual(wizard.n_steps, 2)
        self.assertFalse(wizard._get_payment_mode_buttons())
        # the emptiness is the flow's decision, not an empty lookup
        self.assertIn(self.digital_mode, wizard._get_offered_payment_modes())

    # === Which modes get a button ===

    def test_buttons_offer_the_published_modes_of_the_company(self):
        wizard = self._wizard()
        buttons = wizard._get_payment_mode_buttons()
        self.assertEqual(buttons, self.digital_mode | self.bank_mode)
        self.assertNotIn(self.unpublished_mode, buttons)
        self.assertNotIn(self.foreign_mode, buttons)
        # archived modes are gone too: the button list and the server-side
        # check in _get_validated_payment_mode must agree on the same rules
        self.bank_mode.active = False
        self.assertEqual(wizard._get_payment_mode_buttons(), self.digital_mode)

    def test_button_lookup_is_the_lookup_the_dropdown_uses(self):
        # one lookup for both, so a mode can never be offered by one and
        # unknown to the other
        wizard = self._wizard()
        self.assertEqual(
            wizard._get_payment_mode_buttons(), wizard._get_offered_payment_modes()
        )

    def test_a_buttons_mode_passes_the_server_side_check(self):
        wizard = self._wizard(payment_method=self.digital_mode.id)
        self.assertIn(self.digital_mode, wizard._get_payment_mode_buttons())
        self.assertEqual(
            wizard._get_validated_payment_mode(self.website_company),
            self.digital_mode,
        )

    # === Pressing a button ===

    def test_pressing_a_mode_button_picks_it_and_ends_the_flow(self):
        # what the step call posts when a mode button is pressed: the whole
        # page in one go, ids as strings like any posted form
        wizard = self._wizard()
        wizard.update(
            {
                "sponsorship_type": "standard",
                "email": "one-page@example.org",
                "privacy_consent": True,
                "sponsorship_plus": True,
                "payment_method": str(self.digital_mode.id),
                "action": "next",
            }
        )
        self.assertEqual(wizard.email, "one-page@example.org")
        self.assertTrue(wizard.privacy_consent)
        self.assertTrue(wizard.sponsorship_plus)
        self.assertEqual(wizard.payment_method, self.digital_mode)
        # one page, so the same click that picked the mode finishes the
        # wizard and hands over to /my2/new-sponsorship/submit
        self.assertTrue(wizard.is_done)

    def test_write_and_pray_page_still_continues_to_its_options(self):
        wizard = self._wizard(sponsorship_type="write_and_pray")
        wizard.update(
            {
                "sponsorship_type": "write_and_pray",
                "email": "one-page-wap@example.org",
                "privacy_consent": True,
                "action": "next",
            }
        )
        self.assertFalse(wizard.is_done)
        self.assertEqual(wizard.current_step, self.env.ref(WAP_STEP))
        self.assertFalse(wizard.payment_method)

    def test_switching_to_standard_lands_back_on_the_payment_choice(self):
        # the age modal of the Write&Pray options step offers a standard
        # sponsorship instead. The standard flow is one page shorter, so
        # without the index being clamped the switch would finish the wizard
        # on the spot - a standard sponsorship with no payment mode, never
        # charged.
        wizard = self._wizard(sponsorship_type="write_and_pray")
        wizard.update({"sponsorship_type": "write_and_pray", "action": "next"})
        self.assertEqual(wizard.current_step_idx, 1)
        wizard.update({"sponsorship_type": "standard", "action": "next"})
        self.assertFalse(wizard.is_done)
        self.assertEqual(wizard.current_step_idx, 0)
        self.assertEqual(wizard.current_step, self.env.ref(FAST_CHECKOUT_STEP))
        self.assertTrue(wizard._get_payment_mode_buttons())

    # === The rendered page ===

    def test_page_holds_the_email_the_consent_and_a_button_per_mode(self):
        html = self._render(self._wizard())
        self.assertIn('name="email"', html)
        self.assertIn('name="privacy_consent"', html)
        # sponsorship+ stays opt-in, and moved onto this page with the rest
        self.assertIn('name="sponsorship_plus"', html)
        for mode in (self.digital_mode, self.bank_mode):
            self.assertIn(f'data-payment-mode="{mode.id}"', html)
            self.assertIn(mode.name, html)
        self.assertNotIn(f'data-payment-mode="{self.unpublished_mode.id}"', html)
        # no dropdown and no generic submit next to the buttons
        self.assertNotIn('id="payment_method"', html)
        self.assertNotIn('id="finish_button"', html)

    def test_write_and_pray_page_keeps_the_plain_continue_button(self):
        html = self._render(self._wizard(sponsorship_type="write_and_pray"))
        self.assertIn('name="email"', html)
        self.assertNotIn("data-payment-mode", html)
        self.assertNotIn('name="sponsorship_plus"', html)
        self.assertIn('id="finish_button"', html)

    def test_logged_in_page_keeps_the_dropdown_and_the_finish_button(self):
        html = self._render(self._wizard(public=False))
        self.assertIn('id="payment_method"', html)
        self.assertIn('name="sponsorship_plus"', html)
        self.assertIn('id="finish_button"', html)
        self.assertNotIn("data-payment-mode", html)
