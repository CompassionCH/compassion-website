##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#    @author: Sebastien Toth <popod@me.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_muskathlon = fields.Boolean(
        compute="_compute_is_muskathlon", help="tells if it's a Muskathlon participant"
    )

    def _compute_is_muskathlon(self):
        for partner in self:
            partner.is_muskathlon = any(
                partner.registration_ids.mapped("is_muskathlon")
            )

    def write(self, vals):
        # Mark child protection charter task done when charter is signed
        res = super().write(vals)
        if vals.get("date_agreed_child_protection_charter"):
            self.mapped("registration_ids.task_ids").filtered(
                lambda t: t.task_id
                == self.env.ref("muskathlon.task_sign_child_protection")
            ).write({"done": True})
        return res


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def signup(self, values, token=None):
        """Mark acccount activation task done for Muskathlon participant."""
        res = super().signup(values, token)
        login = res[1]
        user = self.env["res.users"].search([("login", "=", login)])
        registrations = user.partner_id.registration_ids
        registrations.mapped("task_ids").filtered(
            lambda t: t.task_id == self.env.ref("muskathlon.task_activate_account")
        ).write({"done": True})
        return res
