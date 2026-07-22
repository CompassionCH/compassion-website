##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
