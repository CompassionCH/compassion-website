import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    # Stands in for the sponsor's name between the fast-checkout payment and
    # the moment their real name is known. Deliberately not name-shaped: it
    # must never read as a real name, nor fuzzy-match one in res.partner.match.
    # A single token also keeps payment_utils.split_partner_name from raising.
    MY2_PLACEHOLDER_NAME = "(pending)"

    my2_name_placeholder = fields.Boolean(
        string="Name is a placeholder",
        readonly=True,
        copy=False,
        help="The partner was created by a fast checkout before its sponsor"
        " gave their name. Everything that greets the sponsor by name waits"
        " for _my2_replace_placeholder_name to clear this flag.",
    )

    # True if partner has ever been a sponsor.
    is_sponsor = fields.Boolean(compute="_compute_is_sponsor", compute_sudo=True)

    # True if partner has been a sponsor but is not currently sponsoring a child.
    is_ex_sponsor = fields.Boolean(compute="_compute_is_ex_sponsor", compute_sudo=True)

    # True if the partner has ever made a donation
    is_donor = fields.Boolean(compute="_compute_is_donor", compute_sudo=True)
    # True if the partner can write a letter to a sponsored child
    is_writer = fields.Boolean(
        string="Is letter writer",
        compute="_compute_is_writer",
        compute_sudo=True,
    )

    user_login = fields.Char(
        string="MyCompassion login",
        compute="_compute_user_login",
        inverse="_inverse_user_login",
        tracking=True,
    )

    def _my2_replace_placeholder_name(self, firstname, lastname):
        """Write a sponsor's real name over their fast-checkout placeholder.

        The single entry point for "this name is real now": it is also what
        releases whatever was held back while the name was a placeholder.
        Called from the payment notification handler and from the
        post-payment details form.

        A partner whose name is already real is never touched, so a late
        payment notification can never overwrite what the sponsor typed.

        :return: the partners that were actually renamed.
        """
        updated = self.env["res.partner"]
        for partner in self:
            if not partner.my2_name_placeholder or not (firstname or lastname):
                continue
            partner.sudo().write(
                {
                    "firstname": firstname or False,
                    "lastname": lastname or False,
                    "my2_name_placeholder": False,
                }
            )
            updated |= partner
        updated._my2_on_placeholder_name_replaced()
        return updated

    def _my2_on_placeholder_name_replaced(self):
        """Everything that had to wait for the sponsor's real name.

        Extension point for the flows that complete a fast checkout. Kept
        best-effort: it runs inside payment notification handling, where an
        exception would roll back the recorded payment outcome and make the
        provider redeliver the notification into the same crash.
        """
        if not self:
            return
        try:
            with self.env.cr.savepoint():
                contracts = (
                    self.env["recurring.contract"]
                    .sudo()
                    .search([("partner_id", "in", self.ids)])
                )
                pending = contracts._my2_pending_portal_invitations()
                pending._my2_send_portal_invitation()
        except Exception:
            _logger.error(
                "Could not run the post-placeholder handling of partners %s;"
                " their portal invitation may need to be sent by hand.",
                self.ids,
                exc_info=True,
            )

    def get_portal_sponsorships(self, states=None):
        """Portal sponsorships, with grace handling for child departures.

        A terminated sponsorship whose exit communication has not been sent yet
        (``exit_communication_pending``) is still treated as active: it is
        returned when "active" is requested and withheld from "terminated", so
        the sponsor keeps seeing it until they are informed of the departure.
        """
        sponsorships = super().get_portal_sponsorships()
        if states is None:
            return sponsorships
        if not isinstance(states, list):
            states = [states]

        # only sponsorships which have the specified states
        result = sponsorships.filtered(lambda s: s.state in states)
        # sponsorships which have an exit communication pending
        pending_departures = sponsorships.filtered("exit_communication_pending")

        # add or remove the pending sponsorships based on the requested states
        if "active" in states:
            result |= pending_departures
        if "terminated" in states:
            result -= pending_departures
        return result

    def _compute_user_login(self):
        for partner in self:
            login = partner.mapped("user_ids.login")
            if len(login) > 0:
                partner.user_login = login[0]
            else:
                partner.user_login = False

    def _inverse_user_login(self):
        for partner in self:
            users = partner.user_ids
            if len(users) > 0:
                user = users[0]
                user.login = partner.user_login

    def has_unread_correspondence(self):
        """
        Check if the partner has at least one unread correspondence.
        """

        writable_child_ids = self.sponsorship_ids.child_id.filtered(
            "can_i_write_letter"
        ).ids
        correspondence = (
            self.env["correspondence"]
            .with_user(self.user_id)
            .search(
                [
                    ("partner_id", "=", self.id),
                    ("email_read", "=", False),
                    ("child_id", "in", writable_child_ids),
                    ("direction", "=", "Beneficiary To Supporter"),
                ],
                limit=1,
            )
        )
        return bool(correspondence)

    def _compute_is_sponsor(self):
        all_contracts = self.env["recurring.contract"].search(
            [
                "|",
                ("partner_id", "in", self.ids),
                ("correspondent_id", "in", self.ids),
                ("child_id", "!=", False),
            ]
        )
        contracts_by_partner = {}
        for c in all_contracts:
            if c.partner_id:
                contracts_by_partner.setdefault(c.partner_id.id, []).append(c)
            if c.correspondent_id and c.correspondent_id != c.partner_id:
                contracts_by_partner.setdefault(c.correspondent_id.id, []).append(c)

        for partner in self:
            partner_contracts = contracts_by_partner.get(partner.id, [])
            partner.is_sponsor = any(
                c.state in ["waiting", "active"]
                or (c.state == "terminated" and not c.exit_communication_sent)
                for c in partner_contracts
            )

    def _compute_is_ex_sponsor(self):
        """
        Compute whether the partner is an ex-sponsor.

        This method checks if the partner has been a sponsor in the past but is not
        currently sponsoring a child. It searches for all sponsorship contracts
        associated with the partner and determines if all of them are in a
        'terminated' state (excluding those cancelled).
        """
        for partner in self:
            sponsorships = self.env["recurring.contract"].search(
                [
                    "|",
                    ("partner_id", "=", partner.id),
                    ("correspondent_id", "=", partner.id),
                    ("child_id", "!=", False),
                ],
            )
            partner.is_ex_sponsor = any(
                s.state == "terminated" for s in sponsorships
            ) and all(
                s.state in ["draft", "terminated", "cancelled"] for s in sponsorships
            )

    def _compute_is_donor(self):
        donors_data = self.env["account.move.line"].read_group(
            domain=[
                ("partner_id", "in", self.ids),
                ("payment_state", "=", "paid"),
                ("move_id.move_type", "=", "out_invoice"),
            ],
            fields=["partner_id"],
            groupby=["partner_id"],
        )
        donor_ids = {data["partner_id"][0] for data in donors_data}
        for partner in self:
            partner.is_donor = partner.id in donor_ids

    def _compute_is_writer(self):
        """
        Compute whether the partner can write letters to sponsored children.

        Letters remain allowed while the project is suspended: they are held
        as an "Exception" and auto-resubmitted once it reactivates (see
        sbc_compassion correspondence.create_commkit()).
        """
        for partner in self:
            partner.is_writer = bool(
                partner.sponsorship_ids.with_context(
                    allow_during_suspension=True
                ).filtered_domain(
                    [
                        ("can_write_letter_grace", "=", True),
                        "|",
                        ("partner_id.portal_sponsorships", "=", "all_info"),
                        ("correspondent_id", "=", partner.id),
                    ]
                )
            )
