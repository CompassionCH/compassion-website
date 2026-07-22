from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import TransactionCase


class DigitalSeamCase(TransactionCase):
    """Shared fixtures for the digital-payment seam.

    Also used by provider-specific extension modules (e.g. the Nordic
    Adyen adapter) to test their overrides against the same engine setup.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Digital Seam Test Co"})
        cls.partner = cls.env["res.partner"].create({"name": "Digital Seam Sponsor"})
        cls.pay_method = cls.env.ref("my_compassion.payment_method_psp_token")
        cls.mode = cls.env["account.payment.mode"].create(
            {
                "name": "Digital Seam Test Mode",
                "company_id": cls.company.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.pay_method.id,
                "payment_order_ok": False,
            }
        )

    def _make_digital_contract(self, child=None):
        """A contract on a provider-backed mode, in a company with a working
        sale accounting setup, with a plain product line. Child-less (no
        GMC) unless a child is passed."""
        journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
        self.assertTrue(journal, "the database needs one company with sale accounting")
        company = journal.company_id
        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        # the payment chain needs an account.payment.method matching the
        # provider code to build the journal's payment method line
        if not self.env["account.payment.method"].search(
            [("code", "=", "none"), ("payment_type", "=", "inbound")]
        ):
            self.env["account.payment.method"].sudo().create(
                {"name": "Demo", "code": "none", "payment_type": "inbound"}
            )
        provider = self.env["payment.provider"].create(
            {
                "name": "Digital Seam Pay Provider",
                "code": "none",
                "company_id": company.id,
                "journal_id": bank_journal.id,
                "state": "test",
            }
        )
        provider._ensure_payment_method_line()
        mode = self.env["account.payment.mode"].create(
            {
                "name": "Digital Seam Pay Mode",
                "company_id": company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "payment_provider_id": provider.id,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Digital Seam Payer",
                "country_id": self.env.ref("base.se").id,
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            partner, company, mode
        )
        product = self.env["product.product"].search(
            [
                ("default_code", "=", "sponsorship"),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
        )
        self.assertTrue(product, "the database needs the sponsorship product")
        vals = {
            "partner_id": partner.id,
            "group_id": group.id,
            "type": "O",
            "contract_line_ids": [
                Command.create(
                    {"product_id": product.id, "amount": 100, "quantity": 1}
                )
            ],
        }
        if child:
            vals.update({"type": "S", "child_id": child.id})
        return (
            self.env["recurring.contract"].with_context(no_upsert=True).create(vals)
        )

    def _make_chargeable_invoice(self):
        """An active-cycle situation for the charge cron: a digital contract
        with a posted, due, unpaid invoice and a saved token on its group."""
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        invoice.invoice_date_due = fields.Date.today() - timedelta(days=1)
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env["payment.method"].search([], limit=1)
        token = self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": contract.partner_id.id,
                "provider_ref": f"digital-seam-charge-{contract.id}",
                "payment_details": "4242",
            }
        )
        contract.group_id.payment_token_id = token
        return contract, invoice, token

    def _run_charge_cron(self, send_behaviour):
        with patch.object(
            self.registry["payment.transaction"],
            "_send_payment_request",
            send_behaviour,
        ):
            self.env["recurring.contract.group"]._cron_charge_digital_invoices()
