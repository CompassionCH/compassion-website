##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models


class ChildProtectionForm(models.TransientModel):
    _name = "cms.form.partner.child.protection.charter"
    _description = "Child protection charter form"

    agreed = fields.Boolean(required=True)
    partner_uuid = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        forms = super().create(vals_list)
        for form in forms.filtered("agreed"):
            if form.partner_uuid:
                partner = (
                    self.env["res.partner"]
                    .sudo()
                    .search([("uuid", "=", form.partner_uuid)])
                )
            else:
                partner = self.env.user.partner_id
            partner.agree_to_child_protection_charter()
        return forms
