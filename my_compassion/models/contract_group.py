##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import config
from odoo.tools.misc import hmac as hmac_tool

_logger = logging.getLogger(__name__)

# The scope literal separates the signature domains. A token signed for
# another object, like a checkout link, must never open the update-card
# page.
UPDATE_CARD_TOKEN_SCOPE = "my2-update-card"


class ContractGroup(models.Model):
    _name = "recurring.contract.group"
    _inherit = ["recurring.contract.group", "translatable.model"]

    gender = fields.Selection(store=False)
    total_amount = fields.Float(compute="_compute_total_amount")
    payment_token_id = fields.Many2one(
        "payment.token",
        string="Saved payment token",
        check_company=True,
        domain="[('partner_id', '=', partner_id), ('company_id', '=', company_id)]",
        help="Saved payment instrument charged off-session each month when the "
        "payment mode is backed by an online payment provider.",
    )

    @api.constrains("payment_token_id", "partner_id", "company_id")
    def _check_payment_token(self):
        for group in self.filtered("payment_token_id"):
            token = group.payment_token_id
            if token.company_id != group.company_id:
                raise ValidationError(
                    _("The payment token belongs to another company than the group.")
                )
            if (
                token.partner_id.commercial_partner_id
                != group.partner_id.commercial_partner_id
            ):
                raise ValidationError(
                    _("The payment token belongs to another sponsor than the group.")
                )

    @api.model
    def _find_or_create_group(self, partner, company, payment_mode):
        """Return the (partner, company, payment mode) collection group.

        The triple identifies how one sponsor is billed in one company; the
        wizard attaches every new contract to such a group so the contract's
        related payment_mode_id and company_id are populated. payment_mode may
        be an empty recordset depending on the sponsorship product.the group
        then has no mode and nothing collects until staff manually assign one.
        """
        domain = [
            ("partner_id", "=", partner.id),
            ("company_id", "=", company.id),
            ("payment_mode_id", "=", payment_mode.id if payment_mode else False),
        ]
        group = self.search(domain, order="id desc", limit=1)
        if not group:
            group = self.create(
                {
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "payment_mode_id": payment_mode.id if payment_mode else False,
                }
            )
        return group

    def _compute_total_amount(self):
        for group in self:
            group.total_amount = sum(
                group.contract_ids.filtered(
                    lambda s: s.state not in ["terminated", "cancelled"]
                ).mapped("total_amount")
            )

    @api.model
    def _cron_charge_digital_invoices(self):
        """Charge due invoices of provider-backed payment modes off-session.

        Every posted, due, unpaid invoice whose payment mode is backed by an
        online payment provider is charged against its group's saved token -
        at most once per cycle. Refused charges are retried by the provider
        itself (Adyen Auto Rescue) while the transaction stays pending and
        keeps the one-charge guard closed; there is deliberately no
        Odoo-side retry schedule. Definitive failures are handed to
        the contracts through _on_digital_charge_failed.
        """
        invoices = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
                ("invoice_date_due", "<=", fields.Date.today()),
                ("payment_mode_id.payment_provider_id", "!=", False),
            ]
        )
        for invoice in invoices:
            try:
                self._charge_digital_invoice(invoice)
                self._charge_cursor_commit()
            except Exception:
                self._charge_cursor_rollback()
                _logger.exception(
                    "Off-session charge of invoice id %s crashed. The rest of"
                    " the batch continues.",
                    invoice.id,
                )

    @api.model
    def _my2_pending_charge_timeout_days(self, provider):
        """Days after which a pending off-session charge is given up on.

        Provider specific modules override this with their own recovery
        window.
        """
        return 30

    @api.model
    def _cron_sweep_stale_pending_charges(self):
        """Settle off-session charges whose outcome never arrived.

        A pending charge blocks its invoice for the cron, for the sponsor
        and for the staff. Past the provider's recovery window it counts as
        failed, so the invoice reopens and the sponsor is told.
        """
        pending = self.env["payment.transaction"].search(
            [
                ("state", "=", "pending"),
                ("operation", "=", "offline"),
                ("invoice_ids.payment_mode_id.payment_provider_id", "!=", False),
            ]
        )
        now = fields.Datetime.now()
        for tx in pending:
            timeout = self._my2_pending_charge_timeout_days(tx.provider_id)
            changed = tx.last_state_change
            if changed and (now - changed).days < timeout:
                continue
            try:
                tx._set_error(
                    _(
                        "The provider never reported the outcome of this"
                        " payment. It is given up on after %s days.",
                        timeout,
                    )
                )
                for invoice in tx.invoice_ids:
                    invoice.line_ids.contract_id._on_digital_charge_failed(
                        invoice, tx.state_message
                    )
                self._charge_cursor_commit()
            except Exception:
                self._charge_cursor_rollback()
                _logger.exception(
                    "Could not sweep the stale pending transaction id %s. The"
                    " rest of the batch continues.",
                    tx.id,
                )

    @api.model
    def _charge_cursor_commit(self):
        """Make charge bookkeeping durable - except inside tests, where
        committing the shared cursor is forbidden."""
        if config["test_enable"]:
            self.env.flush_all()
        else:
            self.env.cr.commit()  # pylint: disable=invalid-commit

    @api.model
    def _charge_cursor_rollback(self):
        if not config["test_enable"]:
            self.env.cr.rollback()

    @api.model
    def _charge_digital_invoice(self, invoice, force=False):
        """Charge one invoice against its group's saved token.

        Shared by the daily cron and the manual staff action. Returns the
        transaction, or None when a guard decided the invoice must not be
        charged right now. force (the staff action) retries an invoice whose
        automatic attempt failed; open or successful transactions are never
        overridden.

        Money-safety: the transaction row is committed BEFORE the provider
        is contacted and its outcome right after, so no later crash can
        erase the record of a charge that may have moved money - a
        surviving draft blocks any further automatic attempt (staff cancel
        it after checking the provider's dashboard).
        """
        invoice._my2_serialize_charge_attempts()
        if (
            invoice.move_type != "out_invoice"
            or invoice.state != "posted"
            or invoice.payment_state not in ("not_paid", "partial")
        ):
            # the cron domain guarantees this; the staff/RPC path must not
            # trust a stale form view
            return None
        group = invoice.line_ids.contract_id.group_id
        if len(group) != 1:
            _logger.warning(
                "Invoice %s maps to %d contract groups; off-session charge" " skipped.",
                invoice.name,
                len(group),
            )
            return None
        token = group.payment_token_id
        if not token:
            _logger.info(
                "Invoice %s has no saved token on its group; off-session"
                " charge skipped.",
                invoice.name,
            )
            return None
        provider = group.payment_mode_id.payment_provider_id
        if not token.active or token.provider_id != provider:
            _logger.warning(
                "Invoice %s: the group token is archived or belongs to"
                " another provider than the payment mode; off-session"
                " charge skipped.",
                invoice.name,
            )
            return None
        if not (provider.company_id == group.company_id == invoice.company_id):
            _logger.warning(
                "Invoice %s: provider, group and invoice companies differ;"
                " off-session charge skipped.",
                invoice.name,
            )
            return None
        # One charge request per invoice, ever. A draft may still be
        # finishing at the provider and a done one is money, so both always
        # block. An errored or pending one is released by the forced staff
        # action, which is how a dead charge is recovered. Cancelled
        # transactions never block.
        blocking = invoice.transaction_ids.filtered(
            lambda t: t.state in ("draft", "authorized", "done")
            or (t.state in ("pending", "error") and not force)
        )
        if blocking:
            return None
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": token.payment_method_id.id,
                "token_id": token.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "partner_id": group.partner_id.id,
                "operation": "offline",
                "invoice_ids": [Command.set(invoice.ids)],
            }
        )
        # durable before the provider call: whatever happens next, this
        # row blocks a second automatic charge of the invoice
        self._charge_cursor_commit()
        try:
            tx.with_context(
                **self._digital_charge_context(invoice)
            )._send_payment_request()
        finally:
            # the outcome - or the draft of an interrupted call - must
            # survive any exception raised while handling the response
            self._charge_cursor_commit()
        if tx.state == "done":
            # no shopper session exists to poll the status page: reconcile
            # and notify the contracts on the spot
            try:
                with self.env.cr.savepoint():
                    tx._post_process()
            except Exception:
                # money moved and the transaction is safely done: leave
                # reconciliation to the stock retrying cron
                _logger.exception(
                    "Post-processing of transaction %s failed; the payment"
                    " post-processing cron will retry it.",
                    tx.reference,
                )
                self.env.ref("payment.cron_post_process_payment_tx")._trigger()
        elif tx.state == "error":
            invoice.line_ids.contract_id._on_digital_charge_failed(
                invoice, tx.state_message
            )
        # pending means the provider scheduled its own retries: the
        # terminal webhook settles the case
        return tx

    def _due_digital_invoices(self):
        """Posted, due, unpaid invoices of this group that a sponsor may pay
        online right now.

        The engine's one-charge rule applies: an open transaction excludes
        an invoice (a payment may be in flight). Errored attempts do not.
        Paying them with a fresh card is the whole point of the
        update-card page.
        """
        self.ensure_one()
        invoices = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
                ("invoice_date_due", "<=", fields.Date.today()),
                ("line_ids.contract_id.group_id", "=", self.id),
            ]
        )
        invoices = invoices.filtered(
            lambda invoice: not invoice.transaction_ids.filtered(
                lambda t: t.state in ("draft", "pending", "authorized", "done")
            )
        )
        # one payment, one currency: a (theoretical) mixed-currency arrears
        # set reduces to the earliest invoice's currency so the displayed
        # total always equals the charged amount
        if invoices:
            currency = invoices[0].currency_id
            invoices = invoices.filtered(lambda i: i.currency_id == currency)
        return invoices

    def _my2_update_card_url(self):
        """Absolute, self-authenticating link to the update-card page.

        Made for emails rendered outside any web session, like the
        dunning emails. The signed token lets the sponsor open the page
        without logging in. The link points at the website of the group's
        company, so each country's email stays on its own site.
        """
        self.ensure_one()
        # payment_utils.generate_access_token needs an HTTP request. This
        # method runs from crons and email rendering, so the same
        # signature is computed directly.
        token_str = f"{UPDATE_CARD_TOKEN_SCOPE}|{self.id}|{self.partner_id.id}"
        access_token = hmac_tool(self.env(su=True), "generate_access_token", token_str)
        return (
            f"{self.get_base_url()}/my2/update-card"
            f"?group_id={self.id}&access_token={access_token}"
        )

    @api.model
    def _digital_charge_context(self, invoice):
        """Extension hook: context for one off-session charge request.

        Provider-specific modules opt into their server-side recovery
        features here (e.g. instructing the provider to retry a refused
        charge on its own schedule). The base engine sends none.
        """
        return {}
