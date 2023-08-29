from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    user_login = fields.Char(
        string="MyCompassion login",
        compute="_get_user_login",
        inverse="_set_user_login",
        tracking=True,
    )

    def _get_user_login(self):
        for partner in self:
            login = partner.mapped("user_ids.login")
            if len(login) > 0:
                partner.user_login = login[0]
            else:
                partner.user_login = False

    def _set_user_login(self):
        for partner in self:
            users = partner.user_ids
            if len(users) > 0:
                user = users[0]
                user.login = partner.user_login
