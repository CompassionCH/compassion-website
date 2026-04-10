from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

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
        for partner in self:
            partner.is_sponsor = (
                self.env["recurring.contract"].search_count(
                    [
                        "|",
                        ("partner_id", "=", partner.id),
                        ("correspondent_id", "=", partner.id),
                        "|",
                        ("state", "in", ["waiting", "active"]),
                        "&",
                        ("state", "=", "terminated"),
                        ("is_exit_communication_pending", "=", True),
                        ("child_id", "!=", False),
                    ]
                )
                > 0
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
            ) and all(s.state in ["terminated", "cancelled"] for s in sponsorships)

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
        """
        for partner in self:
            partner.is_writer = bool(
                partner.sponsorship_ids.filtered_domain(
                    [
                        ("can_write_letter", "=", True),
                        "|",
                        ("partner_id.portal_sponsorships", "=", "all_info"),
                        ("correspondent_id", "=", partner.id),
                    ]
                )
            )
