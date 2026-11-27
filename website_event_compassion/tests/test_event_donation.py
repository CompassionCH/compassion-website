##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.website.tools import MockRequest

from ..controllers.my_events import MyEventsController


@tagged("post_install", "-at_install")
class TestEventDonation(AccountTestInvoicingCommon):
    """The donations raised by a participant: paid invoices, and bank
    statement lines booked directly on the income account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        now = datetime.now()
        # The event and its registration are set up by the event staff
        cls.event = (
            cls.env["crm.event.compassion"]
            .sudo()
            .create(
                {
                    "name": "Donation test event",
                    "type": "sport",
                    "start_date": now,
                    "end_date": now + timedelta(days=1),
                    "hold_start_date": now.date(),
                    "user_id": cls.env.uid,
                }
            )
        )
        odoo_event = (
            cls.env["event.event"]
            .sudo()
            .create(
                {
                    "name": "Donation test event",
                    "date_begin": now,
                    "date_end": now + timedelta(days=1),
                    "compassion_event_id": cls.event.id,
                    "sponsorship_donation_value": 0,
                }
            )
        )
        cls.ambassador_user = new_test_user(
            cls.env, login="donation_test_ambassador", groups="base.group_portal"
        )
        cls.ambassador = cls.ambassador_user.partner_id
        cls.registration = (
            cls.env["event.registration"]
            .sudo()
            .create({"event_id": odoo_event.id, "partner_id": cls.ambassador.id})
        )
        cls.donor = cls.env["res.partner"].create({"name": "Donation test donor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Donation test fund",
                "type": "service",
                "categ_id": cls.env.ref(
                    "sponsorship_compassion.product_category_fund"
                ).id,
            }
        )
        cls.income_account = cls.company_data["default_account_revenue"]
        cls.bank_journal = cls.company_data["default_journal_bank"]

    def _donation_vals(self):
        return {
            "product_id": self.product.id,
            "user_id": self.ambassador.id,
            "analytic_distribution": {str(self.event.analytic_id.id): 100},
        }

    def _invoice(self, amount, paid):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.donor.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "price_unit": amount,
                            "tax_ids": [Command.clear()],
                            **self._donation_vals(),
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        if paid:
            self.env["account.payment.register"].with_context(
                active_model="account.move", active_ids=invoice.ids
            ).create({"journal_id": self.bank_journal.id})._create_payments()
        return invoice

    def _bank_donation(self, amount):
        """A bank statement line reconciled without invoice: its suspense line
        is booked on the income account, as the reconcile widget does."""
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": fields.Date.today(),
                "amount": amount,
                "payment_ref": "Donation test bank",
                "partner_id": self.donor.id,
            }
        )
        suspense = statement_line.move_id.line_ids.filtered(
            lambda line: line.account_id == self.bank_journal.suspense_account_id
        )
        suspense.with_context(skip_account_move_synchronization=True).write(
            {"account_id": self.income_account.id, **self._donation_vals()}
        )
        return statement_line.move_id.line_ids.filtered("user_id")

    def _misc_entry(self, amount):
        """A posted miscellaneous entry on the income account: no money
        received."""
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "partner_id": self.donor.id,
                            "debit": amount,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.income_account.id,
                            "credit": amount,
                            **self._donation_vals(),
                        }
                    ),
                ],
            }
        )
        entry.action_post()
        return entry.line_ids.filtered("user_id")

    def _create_donations(self):
        paid = self._invoice(30, paid=True)
        self._invoice(20, paid=False)
        bank_donation = self._bank_donation(50)
        bank_refund = self._bank_donation(-10)
        misc = self._misc_entry(40)
        self.assertEqual(paid.payment_state, "paid")
        self.assertEqual(
            (bank_donation | bank_refund | misc).event_id,
            self.event,
        )

    def test_amount_raised(self):
        """Paid invoices and bank lines count, a bank refund reduces the
        total; unpaid invoices and other entries do not count."""
        self._create_donations()
        self.registration.invalidate_recordset(["amount_raised"])
        self.assertEqual(self.registration.amount_raised, 70)

    def test_donation_list_of_the_ambassador(self):
        """The ambassador sees the same donations in their portal."""
        self._create_donations()
        env = self.env(user=self.ambassador_user)
        registration = self.registration.with_env(env)
        with MockRequest(env):
            donations = MyEventsController().get_donations(registration)
        self.assertEqual(
            sorted(float(donation["amount"]) for donation in donations),
            [-10.0, 30.0, 50.0],
        )
