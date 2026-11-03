from unittest.mock import patch

from odoo import Command
from odoo.tests import HttpCase, tagged

from ..controllers.my2_sponsorships import (
    OWN_SIGNUPS_SESSION_KEY,
    own_signup_session_entry,
)
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
        # without the donor's email: name and postcode alone used to match
        "name and postcode": {
            "email": "someone-else@example.org",
            "firstname": "Known",
            "lastname": "Donor",
            "zip": "1400",
        },
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
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "login": "known-donor-login",
                    "partner_id": self.donor.id,
                    "groups_id": [Command.set(self.env.ref("base.group_portal").ids)],
                }
            )
        )
        sponsorship = self._sign_up(user=user)
        self.assertEqual(sponsorship.partner_id, self.donor)
        self.assertEqual(sponsorship.group_id, self.donor_group)

    def test_a_merge_keeps_the_donors_own_flags(self):
        visitor = self._sign_up().partner_id
        self.assertTrue(visitor.my2_email_unverified)
        self.assertTrue(visitor.my2_name_placeholder)
        self.env["base.partner.merge.automatic.wizard"]._merge(
            (visitor | self.donor).ids, self.donor
        )
        self.assertFalse(visitor.exists())
        self.assertFalse(self.donor.my2_email_unverified)
        self.assertFalse(self.donor.my2_name_placeholder)


NOTE = "A visitor sponsored with the email of"


@tagged("post_install", "-at_install")
class TestPossibleDuplicateFlag(UnverifiedSignupCase):
    """The staff are told about a visitor who used a known donor's email,
    once the signup is confirmed and the sponsor has a real name."""

    def setUp(self):
        super().setUp()
        self.reviewer = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Duplicates Reviewer",
                    "login": "duplicates-reviewer",
                    "email": "reviewer@example.org",
                    "groups_id": [Command.set(self.env.ref("base.group_user").ids)],
                }
            )
        )
        self.website = self.env["website"].create(
            {
                "name": "Duplicates Test Website",
                "company_id": self.donor_group.company_id.id,
                "my2_duplicate_review_user_id": self.reviewer.id,
            }
        )

    def _activities(self, partner):
        return self.env["mail.activity"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )

    def _notes(self, partner):
        return partner.message_ids.filtered(lambda m: NOTE in (m.body or ""))

    def _confirm(self, sponsorship):
        """The first payment activates the signup. GMC is out of scope."""
        sponsorship._ensure_first_invoice()
        with patch.object(
            self.registry["gmc.message"],
            "_perform_outgoing_action",
            lambda message_self: None,
        ):
            sponsorship.contract_active()
        self.assertEqual(sponsorship.state, "active")

    def test_the_reviewer_is_told_once_the_signup_is_confirmed(self):
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")
        partner = sponsorship.partner_id
        # an abandoned checkout asks nothing of the staff
        self.assertFalse(self._notes(partner))
        self.assertFalse(self._activities(partner))
        self._confirm(sponsorship)
        activity = self._activities(partner)
        self.assertEqual(activity.user_id, self.reviewer)
        note = self._notes(partner)
        self.assertEqual(len(note), 1)
        # written by the system, not by the website's public user
        self.assertNotEqual(note.author_id, self.env.ref("base.public_partner"))
        # both name the known donor with a link to their record
        for body in (activity.note, note.body):
            self.assertIn(f'data-oe-id="{self.donor.id}"', str(body).replace("'", '"'))
        # and only once
        partner._my2_flag_possible_duplicate(sponsorship.company_id)
        self.assertEqual(len(self._notes(partner)), 1)
        self.assertEqual(len(self._activities(partner)), 1)

    def test_a_fast_checkout_is_flagged_under_its_real_name(self):
        sponsorship = self._sign_up()
        partner = sponsorship.partner_id
        self.assertTrue(partner.my2_name_placeholder)
        self._confirm(sponsorship)
        self.assertFalse(self._activities(partner))
        partner._my2_replace_placeholder_name("Known", "Donor")
        activity = self._activities(partner)
        self.assertEqual(activity.user_id, self.reviewer)
        self.assertNotIn(partner.MY2_PLACEHOLDER_NAME, activity.res_name)

    def test_without_a_reviewer_the_note_is_still_left(self):
        self.website.my2_duplicate_review_user_id = False
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")
        self._confirm(sponsorship)
        self.assertFalse(self._activities(sponsorship.partner_id))
        self.assertTrue(self._notes(sponsorship.partner_id))

    def test_a_new_email_is_not_flagged(self):
        sponsorship = self._sign_up(
            email="brand-new-sponsor@example.org", firstname="New", lastname="One"
        )
        self._confirm(sponsorship)
        self.assertFalse(self._notes(sponsorship.partner_id))

    def test_a_failing_flag_never_breaks_the_confirmation(self):
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")

        def broken(partner_self, company):
            raise ValueError("the reviewer's email could not be rendered")

        with (
            patch.object(
                self.registry["res.partner"], "_my2_post_possible_duplicate", broken
            ),
            self.assertLogs("odoo.addons.my_compassion.models.res_partner", "ERROR"),
        ):
            self._confirm(sponsorship)
        self.assertFalse(sponsorship.partner_id.my2_duplicate_flagged)


@tagged("post_install", "-at_install")
class TestUnverifiedSignupSession(HttpCase, UnverifiedSignupCase):
    """The browser that checked out owns the new signup, and nothing else."""

    def test_the_session_opens_only_its_own_signup(self):
        sponsorship = self._sign_up(firstname="Known", lastname="Donor")
        self.authenticate(
            None,
            None,
            session_extra={
                OWN_SIGNUPS_SESSION_KEY: [own_signup_session_entry(sponsorship)]
            },
        )
        own = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )
        self.assertEqual(own.status_code, 200)
        donors = self.url_open(
            "/my2/new-sponsorship/thank-you" f"?sponsorship_id={self.donor_contract.id}"
        )
        self.assertEqual(donors.status_code, 404)
        # staff move the signup onto the donor: this browser loses it
        sponsorship.partner_id = self.donor
        moved = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={sponsorship.id}"
        )
        self.assertEqual(moved.status_code, 404)
