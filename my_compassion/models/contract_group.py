##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, api, fields, models


class ContractGroup(models.Model):
    _name = "recurring.contract.group"
    _inherit = ["recurring.contract.group", "translatable.model"]

    active = fields.Boolean(default=True)
    payment_token_id = fields.Many2one("payment.token", string="Payment Token")
    gender = fields.Selection(related="partner_id.gender", store=True, readonly=False)
    total_amount = fields.Float(compute="_compute_total_amount")

    active_contract_count = fields.Integer(
        string="Active Contracts Count", compute="_compute_active_contract_count"
    )

    @api.depends("contract_ids.state")
    def _compute_active_contract_count(self):
        for group in self:
            group.active_contract_count = len(
                group.contract_ids.filtered(
                    lambda s: s.state not in ["terminated", "cancelled"]
                )
            )

    def _compute_total_amount(self):
        for group in self:
            group.total_amount = sum(
                group.contract_ids.filtered(
                    lambda s: s.state not in ["terminated", "cancelled"]
                ).mapped("total_amount")
            )

    def get_payment_method_info(self):
        """
        Returns a dict containing display info for the group's payment method.
        Used in MyCompassion2.0 portal.
        """
        self.ensure_one()

        # Default / Fallback values
        info = {
            "icon": False,
            "ref_number": False,
            "label": _("Unknown Method"),
            "expire_date": False,
            "is_card": False,
            "mode_id": self.payment_mode_id.id if self.payment_mode_id else False,
            "group_id": self.id,
        }

        if not self.payment_mode_id:
            return info

        all_icons = self.env["payment.icon"].sudo().search([("image", "!=", False)])
        for icon in all_icons:
            if icon.name.lower() in self.payment_mode_id.name.lower():
                info["icon"] = icon.id
                break

        # Basic Mode Info
        info["label"] = self.payment_mode_id.display_name
        info["type"] = "mode"
        info["ref_number"] = self.bvr_reference if self.bvr_reference else False

        return info

    def change_payment_method(self, new_group_id=None, new_bvr_ref=None):
        """
        Update the contract group by either merging into an existing group
        (if new_group_id provided) or finding/creating a group for a specific
        payment mode (if payment_mode_id provided).
        """
        self.ensure_one()

        # Merge into another Payment Group
        if new_group_id:
            target_group = self.env["recurring.contract.group"].browse(
                int(new_group_id)
            )

            # Validation: Target must exist and belong to the same partner
            if not target_group.exists() or target_group.partner_id != self.partner_id:
                return False

            # Avoid self-merge
            if target_group.id == self.id:
                return True

            # Move all contracts to the target group
            self.active_contract_ids.write({"group_id": target_group.id})
            return True

        # Update Reference (e.g. manual BVR or LSV reference update)
        if new_bvr_ref is not None:
            # Updating the reference for the current group
            self.write({"bvr_reference": new_bvr_ref})
            return True

        return False
