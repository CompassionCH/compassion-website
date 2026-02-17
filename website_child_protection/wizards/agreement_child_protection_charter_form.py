##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ChildProtectionForm(models.TransientModel):
    _name = "cms.form.partner.child.protection.charter"
    _description = "Child protection charter form"

    read_check = fields.Boolean(string="Read and Understood")
    validation_check = fields.Boolean(string="Aware of Violation Consequences")
    legal_check = fields.Boolean(string="Legal Action Awareness")
    understand_check = fields.Boolean(string="Understand Update")
    partner_uuid = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not all([
                vals.get('read_check'),
                vals.get('validation_check'),
                vals.get('legal_check'),
                vals.get('understand_check')
            ]):
                raise ValidationError(_("You must check all boxes to proceed."))

        forms = super(ChildProtectionForm, self).create(vals_list)
        for form in forms:
            if form.partner_uuid:
                partner = (
                    self.env["res.partner"]
                    .sudo()
                    .search([("uuid", "=", form.partner_uuid)])
                )
            else:
                partner = self.env.user.partner_id
            partner.write(
                {"date_agreed_child_protection_charter": fields.Datetime.now()}
            )
        return forms
