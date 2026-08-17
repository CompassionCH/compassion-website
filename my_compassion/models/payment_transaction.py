import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    my2_card_update_group_id = fields.Many2one(
        "recurring.contract.group",
        string="Card Update Group",
        readonly=True,
        help="Contract group whose saved instrument this validation"
        " transaction replaces (the update-card page with nothing due).",
    )

    def _my2_cancel_stale_checkout_tx(self):
        """Cleanup for shopper checkouts that never finished.

        A draft never reached the provider, so cancelling it is safe and
        frees the invoice it blocks. Scheduled per transaction at pay-click.

        Only drafts are cancelled. The provider owns the outcome of a
        pending transaction, which _cron_sweep_stale_pending_charges closes
        once the provider's window has passed.
        """
        self = self.sudo()  # scheduled from a public checkout session
        for tx in self.filtered(lambda t: t.state == "draft"):
            tx._set_canceled(state_message=_("The checkout was abandoned."))

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
                "line_ids.contract_id.group_id.payment_mode_id.payment_provider_id"
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
                # A group with no saved card takes the one that just paid.
                # Replacing an existing card is only allowed from the
                # update-card page, which authenticates the sponsor first.
                groups = (
                    digital_invoices.line_ids.contract_id.group_id
                    | tx.my2_card_update_group_id
                ).filtered(
                    lambda g, tx=tx: g.payment_mode_id.payment_provider_id
                    and g.payment_token_id != tx.token_id
                    and (not g.payment_token_id or g == tx.my2_card_update_group_id)
                )
                try:
                    groups.payment_token_id = tx.token_id
                except (ValidationError, UserError):
                    # A token incompatible with the group must never wedge the
                    # post-processing poll or cron into an eternal retry. The
                    # partner constraint raises one error, the company the
                    # other.
                    _logger.error(
                        "Could not save token %s on groups %s (tx %s);"
                        " monthly charges keep using the previous card.",
                        tx.token_id.id,
                        groups.ids,
                        tx.reference,
                        exc_info=True,
                    )
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
