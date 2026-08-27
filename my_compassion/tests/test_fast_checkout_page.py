from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
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

    # === Finishing a Write&Pray ===

    def test_write_and_pray_finish_takes_no_payment(self):
        """The pay-first checkout must not have taught Write&Pray to pay.

        Write&Pray is the one flow that shares finish_sponsorship() without
        ever taking money, so it is also the one a pay-first rewrite can break
        without anyone noticing: a payment mode reaching its contract would
        hand its invoices to the charge cron, and its sponsor would be debited
        for something they were promised is free. The mode is picked on the
        page on purpose here - it has to be ignored, not merely absent.
        """
        wizard = self._wizard(
            sponsorship_type="write_and_pray",
            email="one-page-wap-finish@example.org",
            privacy_consent=True,
            country=self.env.ref("base.ch").id,
            birthdate=fields.Date.today() - relativedelta(years=20),
            wap_contribution_amount=15.0,
            payment_method=self.digital_mode.id,
        )
        # child_sponsored drives the GMC hold state and is out of scope here,
        # stubbed the way the other finish_sponsorship tests stub it. The line
        # builder is left real: which lines a Write&Pray ends up with is part
        # of what is under test.
        with patch.object(
            self.registry["compassion.child"],
            "child_sponsored",
            lambda child_self, sponsor_id: None,
        ):
            sponsorship = wizard.finish_sponsorship()
        self.assertEqual(sponsorship.type, "SWP")
        self.assertEqual(sponsorship.child_id, self.child)
        self.assertTrue(sponsorship.my2_signup)
        # no mode on the contract, none on its group either: the group is
        # what the charge cron reads the provider off
        self.assertFalse(sponsorship.payment_mode_id)
        self.assertFalse(sponsorship.group_id.payment_mode_id)
        # the contribution the Write&Pray step asked for, and nothing else:
        # no sponsorship amount and no Sponsorship+ line
        self.assertEqual(sponsorship.total_amount, 15.0)
        # the fast-checkout step did happen, so its sponsor is a placeholder
        # waiting for the details form like any other, and the consent tick
        # was persisted
        self.assertTrue(sponsorship.partner_id.my2_name_placeholder)
        self.assertTrue(sponsorship.partner_id.legal_agreement_date)

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

    # === A company that has published no mode ===

    def test_page_without_a_published_mode_offers_no_way_to_finish(self):
        # the state a country is in before its go-live: the modes exist but
        # none is published (Nordic creates them that way, see the Nordic
        # module's hooks.py). The page must not fall back to the generic
        # button, which would finish the wizard with no payment mode at all.
        (self.digital_mode | self.bank_mode).is_published = False
        wizard = self._wizard()
        # still the step the buttons belong to, there is just nothing to
        # make a button of - the two answers are told apart
        self.assertTrue(wizard._step_offers_payment_modes())
        self.assertFalse(wizard._get_payment_mode_buttons())
        html = self._render(wizard)
        self.assertNotIn("data-payment-mode", html)
        self.assertNotIn('id="finish_button"', html)
        # nothing on the page submits it at all
        self.assertNotIn("btn-next", html)

    def test_finishing_without_a_mode_is_refused_before_anything_is_written(self):
        # the page offers no submit, so this is a tampered post - it must not
        # leave a partner or an uncollectable sponsorship behind
        (self.digital_mode | self.bank_mode).is_published = False
        wizard = self._wizard(
            email="one-page-no-mode@example.org",
            privacy_consent=True,
            country=self.env.ref("base.se").id,
        )
        with self.assertRaises(ValidationError):
            wizard.finish_sponsorship()
        self.assertFalse(
            self.env["res.partner"].search(
                [("email", "=", "one-page-no-mode@example.org")]
            )
        )

    def test_logged_in_page_keeps_the_dropdown_and_the_finish_button(self):
        html = self._render(self._wizard(public=False))
        self.assertIn('id="payment_method"', html)
        self.assertIn('name="sponsorship_plus"', html)
        self.assertIn('id="finish_button"', html)
        self.assertNotIn("data-payment-mode", html)
