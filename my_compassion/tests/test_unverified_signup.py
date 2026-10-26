from unittest.mock import patch

from odoo import Command
from odoo.tests import HttpCase, tagged

from ..controllers.my2_sponsorships import OWN_SIGNUPS_SESSION_KEY
from .common import DigitalSeamCase

DONOR_EMAIL = "known-donor@example.org"


class UnverifiedSignupCase(DigitalSeamCase):
    """A known donor, billed by card, and a visitor who sponsors with their
    name, email and postcode without logging in."""

    def setUp(self):
        super().setUp()
        self.donor_contract, self.donor_invoice, self.donor_token = (
            self._make_chargeable_invoice()
        )
        self.donor = self.donor_contract.partner_id
        self.donor.write(
            {
                "firstname": "Known",
                "lastname": "Donor",
                "email": DONOR_EMAIL,
                "zip": "1400",
            }
        )
        self.donor_group = self.donor_contract.group_id
        self.mode = self.donor_contract.payment_mode_id
        self.mode.is_published = True
        self.child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(self.child, "the database needs a child")
        self.product = self.donor_contract.contract_line_ids.product_id

    def _sign_up(self, user=None, **wizard_vals):
        """finish_sponsorship of the one-page checkout, on the donor's
        company and card payment mode."""
        wizard = self.env["new.sponsorship.wizard"].create(
            {
                "sponsorship_type": "standard",
                "user_id": (user or self.env.ref("base.public_user")).id,
                "child_id": self.child.id,
                "company_id": self.donor_group.company_id.id,
                "payment_method": self.mode.id,
                # finish_sponsorship drops the last line without it, and
                # the stub below builds a single one
                "sponsorship_plus": True,
                "email": DONOR_EMAIL,
                "privacy_consent": True,
                "country": self.env.ref("base.ch").id,
                **wizard_vals,
            }
        )
        product = self.product

        def fake_lines(contract_self, correspondence):
            return [
                Command.clear(),
                Command.create(
                    {"product_id": product.id, "amount": 100, "quantity": 1}
                ),
            ]

        # Out of scope here, as in test_multicompany: the GMC hold of the
        # child and the company's full sponsorship product configuration.
        with (
            patch.object(
                self.registry["compassion.child"],
                "child_sponsored",
                lambda child_self, sponsor_id: None,
            ),
            patch.object(
                self.registry["recurring.contract"],
                "_get_sponsorship_standard_lines",
                fake_lines,
            ),
        ):
            return wizard.finish_sponsorship()


@tagged("post_install", "-at_install")
class TestUnverifiedSignup(UnverifiedSignupCase):
    # What the visitor may type: nothing but the email (the deferred
    # details of the fast checkout), or a name and a postcode as well.
    IDENTITIES = {
        "email only": {},
        "name": {"firstname": "Known", "lastname": "Donor"},
        "name and postcode": {"firstname": "Known", "lastname": "Donor", "zip": "1400"},
    }

    def test_a_visitor_never_gets_the_known_donor(self):
        donor_values = self.donor.read(
            ["name", "email", "zip", "country_id", "legal_agreement_date"]
        )
        for case, identity in self.IDENTITIES.items():
            with self.subTest(case):
                sponsorship = self._sign_up(**identity)
                partner = sponsorship.partner_id
                self.assertNotEqual(partner, self.donor)
                self.assertTrue(partner.my2_email_unverified)
                self.assertEqual(
                    partner.my2_name_placeholder, not identity, "placeholder"
                )
                group = sponsorship.group_id
                self.assertNotEqual(group, self.donor_group)
                self.assertEqual(group.partner_id, partner)
                self.assertFalse(group.payment_token_id)
        self.assertEqual(self.donor_group.contract_ids, self.donor_contract)
        self.assertEqual(self.donor_group.payment_token_id, self.donor_token)
        self.assertEqual(
            self.donor.read(
                ["name", "email", "zip", "country_id", "legal_agreement_date"]
            ),
            donor_values,
        )

    def test_the_signup_is_never_charged_on_the_donors_card(self):
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")
        invoice = sponsorship._ensure_first_invoice()
        invoice.invoice_date_due = self.donor_invoice.invoice_date_due
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        # the donor's own invoice is charged on their card, as before
        self.assertEqual(self.donor_invoice.transaction_ids.token_id, self.donor_token)
        # the visitor's has no card to be charged on: their own first
        # payment (the checkout) is the only way it is ever paid
        self.assertFalse(invoice.transaction_ids)
        self.assertFalse(
            self.env["payment.transaction"].search(
                [
                    ("token_id", "=", self.donor_token.id),
                    ("invoice_ids", "in", invoice.ids),
                ]
            )
        )

    def test_a_logged_in_donor_keeps_their_group(self):
        user = self.env["res.users"].create(
            {
                "login": "known-donor-login",
                "partner_id": self.donor.id,
                "groups_id": [Command.set(self.env.ref("base.group_portal").ids)],
            }
        )
        sponsorship = self._sign_up(user=user)
        self.assertEqual(sponsorship.partner_id, self.donor)
        self.assertEqual(sponsorship.group_id, self.donor_group)

    def test_the_staff_is_told_about_a_possible_duplicate(self):
        website = self.env["website"].get_current_website()
        website.my2_duplicate_review_user_id = self.env.user
        partner = self._sign_up(firstname="Known", lastname="Donor").partner_id
        activity = self.env["mail.activity"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(activity.user_id, self.env.user)
        # both name the known donor with a link to their record
        for body in (activity.note, partner.message_ids[0].body):
            self.assertIn(f'data-oe-id="{self.donor.id}"', str(body).replace("'", '"'))

    def test_without_a_reviewer_the_note_is_still_left(self):
        website = self.env["website"].get_current_website()
        website.my2_duplicate_review_user_id = False
        partner = self._sign_up().partner_id
        self.assertFalse(
            self.env["mail.activity"].search(
                [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
            )
        )
        self.assertIn("A visitor sponsored with the email", partner.message_ids[0].body)

    def test_a_new_email_is_not_flagged(self):
        partner = self._sign_up(email="brand-new-sponsor@example.org").partner_id
        self.assertFalse(
            partner.message_ids.filtered(
                lambda m: "A visitor sponsored with the email" in (m.body or "")
            )
        )


@tagged("post_install", "-at_install")
class TestUnverifiedSignupSession(HttpCase, UnverifiedSignupCase):
    """The browser that checked out owns the new signup, and nothing else."""

    def test_the_session_opens_only_its_own_signup(self):
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")
        self.authenticate(
            None, None, session_extra={OWN_SIGNUPS_SESSION_KEY: [sponsorship.id]}
        )
        own = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )
        self.assertEqual(own.status_code, 200)
        donors = self.url_open(
            "/my2/new-sponsorship/thank-you" f"?sponsorship_id={self.donor_contract.id}"
        )
        self.assertEqual(donors.status_code, 404)
