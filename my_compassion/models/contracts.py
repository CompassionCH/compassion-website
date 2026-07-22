import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class RecurringContract(models.Model):
    """
    Extends the recurring.contract model for MyCompassion features.

    Inheriting "utm.mixin" makes sure that the model integrates Odoo's utm features.
    This allows Odoo to automatically intercept UTM cookies.
    """

    _name = "recurring.contract"
    _inherit = ["recurring.contract", "utm.mixin"]

    REVERT_DELAY_MINUTES = 15

    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
    )

    def _compute_can_show_on_my_compassion(self):
        """
        Return if a contract is active or terminated,
        or if the contract is new (not cancelled and without parent)
        """
        for contract in self:
            contract.can_show_on_my_compassion = contract.state in [
                "active",
                "terminated",
            ] or (contract.state != "cancelled" and not contract.parent_id)

    def _ensure_first_invoice(self):
        """Bring the contract to waiting and return its earliest open invoice.

        Invoice generation is normally a queue job (with_delay_sh); the
        checkout request needs the invoice NOW to link the transaction, so the
        chain runs under queue_job__no_delay. Idempotent: an existing open
        invoice is returned as-is. Advance billing may post several invoices -
        only the earliest is the first charge.
        """
        self.ensure_one()
        sync = self.with_context(queue_job__no_delay=True)
        if self.state == "draft":
            sync.contract_waiting()
        invoices = self.invoice_line_ids.move_id.filtered(
            lambda m: m.state == "posted"
            and m.payment_state in ("not_paid", "partial")
        )
        return invoices.sorted("invoice_date")[:1]

    def _schedule_digital_revert(self):
        """One-shot delayed cleanup after a pay-click: if no payment
        succeeds within the delay, the signup is reverted."""
        self.ensure_one()
        self.with_delay_sh(
            "_revert_abandoned_digital_signup",
            eta=self.REVERT_DELAY_MINUTES * 60,
            identity_key=f"digital_revert.{self.id}",
        )

    def _revert_abandoned_digital_signup(self, reschedule=True):
        """Cleanup for digital signups that never paid: cancel the contract
        and its open invoice, release the child to the pool, keep the
        partner as a lead. A done/authorized tx means paid -> no-op; a
        pending tx (3DS challenge in flight) or a freshly created one (the
        provider round-trip may be in flight) gets one grace reschedule."""
        self.ensure_one()
        # scheduled from the public checkout session; the cleanup itself
        # needs full access to contracts, moves and the child
        self = self.sudo()
        if self.state not in ("draft", "waiting"):
            # staff already handled the contract (activated, cancelled...):
            # a stale revert must never undo their work
            return
        txs = self.invoice_line_ids.move_id.transaction_ids
        if any(t.state in ("done", "authorized") for t in txs):
            return
        recent = fields.Datetime.now() - timedelta(minutes=5)
        if any(
            t.state == "pending" or (t.state == "draft" and t.create_date >= recent)
            for t in txs
        ):
            if reschedule:
                self.with_delay_sh(
                    "_revert_abandoned_digital_signup",
                    False,
                    eta=self.REVERT_DELAY_MINUTES * 60,
                    identity_key=f"digital_revert.retry.{self.id}",
                )
            return
        # cancel first: the invoice-cleaning filters read the end_date the
        # cancellation stamps
        self._contract_cancelled({})
        self._cancel_invoices()
        child = self.child_id
        if child:
            try:
                # the cancel chain never frees the child (only unlink does)
                child.child_unsponsored()
            except Exception:
                # child_unsponsored ends with a live GMC fetch; its failure
                # must not roll back the cancellation
                _logger.warning(
                    "Digital signup revert: could not release child %s of "
                    "contract %s; release it manually.",
                    child.id,
                    self.id,
                    exc_info=True,
                )
            child.write(
                {
                    "website_reservation_date": False,
                    "website_reservation_id": False,
                }
            )

    def _on_digital_charge_failed(self, invoice, reason):
        """Hook: an off-session charge failed definitively (refused with no
        provider-side rescue, or the rescue window closed without success).

        The dunning pipeline plugs in here; until it exists the failure is
        only logged for staff.
        """
        _logger.warning(
            "Off-session charge of invoice %s failed definitively for "
            "contracts %s: %s",
            invoice.name,
            self.ids,
            reason,
        )
