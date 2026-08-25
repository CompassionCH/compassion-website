import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models

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

    # How long a details token stays usable. Long enough for the "we will
    # email you a link to finish later" path, short enough that a link left
    # in a mailbox or a browser history stops working.
    DETAILS_TOKEN_HOURS = 72

    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
    )
    can_write_letter_grace = fields.Boolean(
        string="Can write letter (incl. suspension)",
        compute="_compute_can_write_letter_grace",
        help="Same as can_write_letter, but also true while the project is"
        " suspended: such letters are held as an 'Exception' and"
        " auto-resubmitted once the project reactivates (see"
        " sbc_compassion correspondence.create_commkit()). Portal views"
        " must read this field instead of can_write_letter directly, or a"
        " terminated-but-in-grace-period sponsorship whose project is"
        " currently suspended will incorrectly show as fully ended.",
    )
    my2_signup = fields.Boolean(
        string="MyCompassion Signup",
        readonly=True,
        help="The sponsorship was created by the sponsor through the"
        " MyCompassion signup wizard. Such sponsors are invited to create"
        " their portal account once the sponsorship is confirmed.",
    )
    my2_details_token = fields.Char(
        string="Details form token",
        readonly=True,
        copy=False,
        groups="base.group_system",
        help="Write credential of the post-payment details form. See"
        " _my2_issue_details_token.",
    )
    my2_details_token_expiration = fields.Datetime(
        string="Details form token expiration",
        readonly=True,
        copy=False,
        groups="base.group_system",
    )

    @api.depends("can_write_letter")
    def _compute_can_write_letter_grace(self):
        for contract in self:
            contract.can_write_letter_grace = contract.with_context(
                allow_during_suspension=True
            ).can_write_letter

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
            lambda m: m.move_type == "out_invoice"
            and m.state == "posted"
            and m.payment_state in ("not_paid", "partial")
        )
        return invoices.sorted("invoice_date")[:1]

    def _my2_details_pending(self):
        """Whether this signup is still waiting for its sponsor's real name.

        The one state in which the details form may write to the partner.
        """
        self.ensure_one()
        return bool(self.my2_signup and self.partner_id.my2_name_placeholder)

    def _my2_issue_details_token(self):
        """Mint the write credential of the post-payment details form.

        Single-purpose, single-use and expiring on all three counts because a
        deterministic, never-expiring token (the payment_utils
        generate_access_token pattern) would be a permanent bearer credential
        to rewrite a sponsor's identity, leaking through URLs, browser history
        and referrers. Constraints this shape has to keep:

        - never handed out on a bare record id: callers must have proved they
          are the session that paid, or be the authenticated sponsor;
        - useless once the name is real (_my2_details_pending), so a
          replayed link cannot overwrite what the sponsor typed;
        - a write credential only. It must never gate a read, or the form
          becomes a "type an email, pay, read the owner's details" endpoint;
        - burnt on the first successful save
          (_my2_consume_details_token).

        Issuing again replaces the previous token, which is what makes the
        page reloadable and the "email me a link to finish later" path
        possible.

        :return: the token, or False when this signup wants no details.
        """
        self.ensure_one()
        if not self._my2_details_pending():
            return False
        token = secrets.token_urlsafe(32)
        self.sudo().write(
            {
                "my2_details_token": token,
                "my2_details_token_expiration": fields.Datetime.now()
                + timedelta(hours=self.DETAILS_TOKEN_HOURS),
            }
        )
        return token

    def _my2_check_details_token(self, token):
        """Whether token may write this signup's missing sponsor details."""
        self.ensure_one()
        this = self.sudo()
        if not token or not this.my2_details_token:
            return False
        if not this.my2_details_token_expiration:
            return False
        if this.my2_details_token_expiration <= fields.Datetime.now():
            return False
        if not this._my2_details_pending():
            return False
        return secrets.compare_digest(str(token), this.my2_details_token)

    def _my2_consume_details_token(self):
        """Burn the details token. Called once the details are saved."""
        self.sudo().write(
            {
                "my2_details_token": False,
                "my2_details_token_expiration": False,
            }
        )

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

    # The sponsor gets the escalation delay to fix their card between the
    # first email and the final one. A fix-it email younger than the
    # episode window blocks any new first email. This way a card that
    # stays broken over several months makes one dunning episode, not one
    # email per failed invoice. These are only the code fallbacks. Staff
    # tune the real values in the system parameters
    # my_compassion.fixit_escalation_days and
    # my_compassion.fixit_episode_days.
    FIXIT_ESCALATION_DAYS = 14
    FIXIT_EPISODE_DAYS = 60

    def _my2_fixit_windows(self):
        """Dunning windows in days, as (escalation, episode).

        Read from the system parameters so staff can tune the cadence
        without a deploy. A broken value falls back to the code default.
        The episode is kept longer than the escalation delay, otherwise
        the escalation search window would be empty.
        """
        get_param = self.env["ir.config_parameter"].sudo().get_param

        def int_param(key, default):
            try:
                return int(get_param(key, default))
            except (TypeError, ValueError):
                _logger.warning(
                    "Invalid system parameter %s, using the default %s.",
                    key,
                    default,
                )
                return default

        escalation = int_param(
            "my_compassion.fixit_escalation_days", self.FIXIT_ESCALATION_DAYS
        )
        episode = int_param("my_compassion.fixit_episode_days", self.FIXIT_EPISODE_DAYS)
        return escalation, max(episode, escalation + 1)

    def _my2_fixit_configs(self):
        """Hook: communication configs of the charge-failure pipeline.

        Returns {"first": config, "final": config}. Empty in this module.
        Each country writes its own emails and supplies the configs
        through an override. Without them failures are only logged.
        """
        return {}

    def _my2_portal_invitation_config(self):
        """Hook: config of the post-signup portal invitation email.

        Empty in this module, for the same reason as _my2_fixit_configs.
        """
        return self.env["partner.communication.config"]

    def _on_digital_charge_failed(self, invoice, reason):
        """An off-session charge failed for good (refused with no
        provider-side rescue, or the rescue window closed without success).

        Starts the fix-it pipeline: one email to the payer with a link to
        the update-card page. The daily escalation cron sends the final
        email and flags staff if the invoices stay unpaid. Does nothing
        but log when no country module supplies the configs.
        """
        _logger.warning(
            "Off-session charge of invoice %s failed definitively for "
            "contracts %s: %s",
            invoice.name,
            self.ids,
            reason,
        )
        configs = self._my2_fixit_configs()
        if not configs:
            return
        # Dunning is best effort. This runs inside payment webhooks and
        # the charge cron. An exception escaping here would fail the
        # webhook and roll back the recorded payment outcome, so the
        # provider would redeliver the webhook into the same crash again
        # and again.
        try:
            with self.env.cr.savepoint():
                self._my2_start_fixit_dunning(configs)
        except Exception:
            _logger.exception(
                "Could not start fix-it dunning for contracts %s. Staff"
                " must follow up on the failed charge of %s.",
                self.ids,
                invoice.name,
            )

    def _my2_start_fixit_dunning(self, configs):
        _escalation, episode = self._my2_fixit_windows()
        to_prompt = self.filtered(
            # The provider can give up weeks after the first refusal. A
            # contract terminated in between, or one with nothing due
            # anymore, must not hear "your sponsorship will continue".
            lambda contract: contract.state in ("active", "mandate")
            and contract.group_id._due_digital_invoices()
            and not contract._my2_find_fixit_jobs(
                configs["first"] | configs["final"],
                fields.Datetime.now() - timedelta(days=episode),
            )
        )
        # The card belongs to the payer, so never mail the correspondent.
        # The email is transactional and goes out without staff review.
        to_prompt.with_context(default_auto_send=True).send_communication(
            configs["first"], correspondent=False
        )

    def _my2_find_fixit_jobs(
        self, configs, since, states=("pending", "processing", "done", "cancel")
    ):
        """Fix-it jobs already covering this contract.

        Cancelled jobs count. When staff cancel a dunning email, that is
        a decision, not a request to send it again. Failed jobs (template
        crash) are excluded by default so a later send can merge into
        them and retry. The escalation check adds them to its states so
        one escalation attempt is always the last one.
        """
        self.ensure_one()
        jobs = self.env["partner.communication.job"].search(
            [
                ("config_id", "in", configs.ids),
                ("state", "in", states),
                ("object_ids", "like", str(self.id)),
                ("create_date", ">=", since),
            ]
        )
        # object_ids is a comma-separated string. The "like" match can
        # also hit a contract whose id simply contains ours, so the ids
        # are checked exactly here.
        return jobs.filtered(lambda j: self.id in j.get_objects().ids)

    @api.model
    def _cron_digital_fixit_escalation(self):
        """Second and last dunning step. FIXIT_ESCALATION_DAYS after the
        first fix-it email, sponsors with invoices still unpaid get the
        final email and staff get an activity on the contract. The
        automation ends there.
        """
        configs = self._my2_fixit_configs()
        if not configs:
            return
        escalation, episode = self._my2_fixit_windows()
        now = fields.Datetime.now()
        first_jobs = self.env["partner.communication.job"].search(
            [
                ("config_id", "=", configs["first"].id),
                ("state", "=", "done"),
                ("sent_date", "<=", now - timedelta(days=escalation)),
                ("sent_date", ">=", now - timedelta(days=episode)),
            ]
        )
        for job in first_jobs:
            contracts = (
                job.get_objects()
                .exists()
                .filtered(
                    lambda c, job=job: c.state in ("active", "mandate")
                    and c.group_id._due_digital_invoices()
                    and not c._my2_find_fixit_jobs(
                        configs["final"],
                        job.sent_date,
                        # "failure" is included so one escalation attempt
                        # is always the last one. Without it a crashed
                        # final email would flag staff again every day.
                        states=("pending", "processing", "done", "cancel", "failure"),
                    )
                )
            )
            if contracts:
                jobs = contracts.with_context(
                    default_auto_send=True
                ).send_communication(configs["final"], correspondent=False)
                if jobs:
                    # An archived config creates no job. In that case no
                    # final email exists and staff must not be told one
                    # was sent.
                    contracts._my2_flag_staff_fixit(configs["final"])

    def _my2_flag_staff_fixit(self, config):
        """Hand the exhausted dunning over to a human."""
        for contract in self:
            contract.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("Card payment failed, automatic dunning exhausted"),
                note=_(
                    "The sponsor's saved card could not be charged and both"
                    " fix-it emails were sent without effect. Please contact"
                    " the sponsor or handle the arrears manually."
                ),
                user_id=(config.user_id or self.env.user).id,
            )

    def contract_active(self):
        res = super().contract_active()
        # A digital signup is confirmed by its first successful payment.
        # That payment is what activates the contract.
        self.filtered(
            lambda c: c.my2_signup
            and c.group_id.payment_mode_id.payment_provider_id
            and not c.partner_id.my2_name_placeholder
        )._my2_send_portal_invitation()
        return res

    def contract_waiting(self):
        res = super().contract_waiting()
        # A bank-collected signup is confirmed when staff validate it.
        # Digital contracts also pass here at pay-click, before any
        # payment, so they are invited on activation instead.
        self.filtered(
            lambda c: c.my2_signup
            and not c.group_id.payment_mode_id.payment_provider_id
            and not c.partner_id.my2_name_placeholder
        )._my2_send_portal_invitation()
        return res

    def _my2_pending_portal_invitations(self):
        """Confirmed signups whose invitation was held back for a name.

        A fast checkout activates the contract before the sponsor has said
        who they are, and the invitation email greets them by name, so it
        waits. Activation itself never does. This is what
        res.partner._my2_on_placeholder_name_replaced calls once the real
        name lands, from the payment notification or the details form.

        The confirmation test mirrors the two hooks above: a digital signup
        is confirmed once active, a bank-collected one once waiting.
        """
        return self.filtered(
            lambda c: c.my2_signup
            and not c.partner_id.my2_name_placeholder
            and (
                c.state == "active"
                if c.group_id.payment_mode_id.payment_provider_id
                else c.state in ("waiting", "active")
            )
        )

    def _my2_send_portal_invitation(self):
        """Invite fresh wizard sponsors to create their MyCompassion
        account once their sponsorship is confirmed.

        One invitation per partner, ever. Sponsors who already have a
        login are left alone. This runs inside payment post-processing
        and contract validation, so it must never break either of them.
        """
        if not self:
            return
        config = self._my2_portal_invitation_config()
        if not config:
            return
        try:
            # The savepoint makes sure a swallowed database error does
            # not leave the surrounding payment cursor unusable.
            with self.env.cr.savepoint():
                job_model = self.env["partner.communication.job"].sudo()
                for partner in self.mapped("partner_id").sudo():
                    has_user = partner.with_context(active_test=False).user_ids
                    if not partner.email or has_user:
                        continue
                    if job_model.search_count(
                        [
                            ("config_id", "=", config.id),
                            ("partner_id", "=", partner.id),
                            ("state", "!=", "cancel"),
                        ]
                    ):
                        continue
                    partner.signup_prepare()
                    job_model.create(
                        {
                            "config_id": config.id,
                            "partner_id": partner.id,
                            "auto_send": True,
                        }
                    )
        except Exception:
            _logger.error(
                "Could not send the portal invitation for contracts %s."
                " The sponsors can still use the password-reset flow.",
                self.ids,
                exc_info=True,
            )
