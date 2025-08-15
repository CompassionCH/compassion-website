from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

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
        """Check if partner has at least one correspondence with email_read set."""
        correspondence = self.env["correspondence"].search([
            ("partner_id", "=", self.id),
            ("email_read", "=", False),
        ], limit=1)
        return bool(correspondence)