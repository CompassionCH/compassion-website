import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        """Post-processing of digital-mode contract payments.

        - Keep the collection group's saved token current: a confirmed
          tokenized transaction is the instrument the monthly off-session
          charge must use from now on.
        - Run invoice_paid on the settled invoices' contracts: provider
          payments reconcile invoices into 'in_payment' (outstanding
          account), which the bank-statement reconcile hook - the usual
          invoice_paid trigger - ignores, so waiting contracts would never
          activate.
        """
        res = super()._post_process()
        for tx in self.filtered(lambda t: t.state == "done"):
            digital_invoices = tx.invoice_ids.filtered(
                lambda m: m.line_ids.contract_id.group_id.payment_mode_id
                .payment_provider_id
            )
            if digital_invoices and not digital_invoices.filtered(
                lambda m: m.state == "posted"
            ):
                # money was captured but every target invoice is gone
                # (e.g. the signup was reverted while the charge was in
                # flight) - surface it, staff must refund or re-post
                _logger.error(
                    "Transaction %s is done but its invoices %s are all "
                    "cancelled: captured payment needs manual handling.",
                    tx.reference,
                    digital_invoices.mapped("name"),
                )
            if tx.token_id:
                groups = digital_invoices.line_ids.contract_id.group_id.filtered(
                    lambda g: g.payment_mode_id.payment_provider_id
                    and g.payment_token_id != tx.token_id
                )
                groups.payment_token_id = tx.token_id
            for invoice in digital_invoices.filtered(
                lambda m: m.payment_state in ("paid", "in_payment")
            ):
                try:
                    invoice.line_ids.contract_id.invoice_paid(invoice)
                except UserError:
                    # e.g. a contract cancelled between charge and
                    # settlement - never break the poll/cron post-processing
                    _logger.error(
                        "invoice_paid failed for invoice %s (tx %s); "
                        "activation/handling left to staff.",
                        invoice.name,
                        tx.reference,
                        exc_info=True,
                    )
        return res
