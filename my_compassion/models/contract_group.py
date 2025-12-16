##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models, _, api


class ContractGroup(models.Model):
    _name = "recurring.contract.group"
    _inherit = ["recurring.contract.group", "translatable.model"]

    active = fields.Boolean(default=True)
    payment_token_id = fields.Many2one("payment.token", string="Payment Token")
    gender = fields.Selection(related="partner_id.gender", store=True, readonly=False)
    total_amount = fields.Float(compute="_compute_total_amount")

    def _compute_total_amount(self):
        for group in self:
            group.total_amount = sum(
                group.contract_ids.filtered(
                    lambda s: s.state not in ["terminated", "cancelled"]
                ).mapped("total_amount")
            )

    # TODO: Revise this method once final logic and needs are clarified
    def get_payment_method_info(self):
        """
        Returns a dict containing display info for the group's payment method.
        Used in MyCompassion2.0 portal.
        """
        self.ensure_one()

        # Default / Fallback values
        info = {
            'icon': False,
            'ref_number': False,
            'label': _('Unknown Method'),
            'expire_date': False,
            'is_card': False,
            'mode_id': self.payment_mode_id.id if self.payment_mode_id else False,
            'group_id': self.id,
        }

        if not self.payment_mode_id:
            return info

        # test for icon retrieval
        # Not that good, could be improved
        all_icons = self.env['payment.icon'].sudo().search([('image', '!=', False)])
        for icon in all_icons:
            if icon.name.lower() in self.payment_mode_id.name.lower():
                info['icon'] = icon.id
                break

        # 1. Basic Mode Info
        info['label'] = self.payment_mode_id.display_name
        info['type'] = 'mode'
        info['ref_number'] = self.bvr_reference if self.bvr_reference else False

        # 2. Check for Linked Token (Primary Strategy)
        valid_token = self.payment_token_id

        if valid_token:
            info.update({
                'type': 'token',
                'token_id': valid_token.id,
                'ref_number': "Not retrieved for now",
                'is_card': True,
            })

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
            target_group = self.env['recurring.contract.group'].browse(int(new_group_id))

            # Validation: Target must exist and belong to the same partner
            if not target_group.exists() or target_group.partner_id != self.partner_id:
                return False

            # Avoid self-merge
            if target_group.id == self.id:
                return True

            # Move all contracts to the target group
            self.contract_ids.write({'group_id': target_group.id})

            # Deactivate the old group if it is now empty to clean up the UI
            if not self.contract_ids:
                self.active = False

            return True

        # Update Reference (e.g. manual BVR or LSV reference update)
        if new_bvr_ref and self.bvr_reference:
            # Updating the reference for the current group
            self.write({'bvr_reference': new_bvr_ref})
            return True


        return False

    @api.model
    def find_or_create(self, partner_id, payment_mode_id, recurring_unit='monthly', recurring_value=1):
        """
        Finds an existing compatible group for the partner/mode or creates a new one.
        Used for adding a new payment method or updating an existing one.

        :param partner_id: int, ID of the res.partner
        :param payment_mode_id: int, ID of the account.payment.mode
        :param recurring_unit: str, 'monthly' (default) or 'yearly'
        :param recurring_value: int, 1 (default)
        :return: recurring.contract.group recordset (single record)
        """
        partner = self.env['res.partner'].browse(partner_id)
        mode = self.env['account.payment.mode'].browse(payment_mode_id)

        if not partner.exists() or not mode.exists():
            return self.browse()

        # Search for existing compatible group
        domain = [
            ('partner_id', '=', partner.id),
            ('payment_mode_id', '=', mode.id),
            ('recurring_unit', '=', recurring_unit),
            ('recurring_value', '=', recurring_value),
        ]

        # We take the most recent one if multiple exist
        group = self.search(domain, limit=1, order='id desc')

        if not group:
            # Create a new group
            # Construct a reference name similar to Odoo standard or your convention
            new_ref = f"{partner.ref or partner.name} - {mode.name}"

            group = self.create({
                'partner_id': partner.id,
                'payment_mode_id': mode.id,
                'recurring_unit': recurring_unit,
                'recurring_value': recurring_value,
                'ref': new_ref,
                'active': True,
            })

        return group


    @api.model
    def create_from_transaction(self, transaction):
        """
        Creates a contract group from a validation transaction.
        Returns a tuple: (group_record, message_string)
        """
        if not transaction or not transaction.payment_token_id:
            return self.browse(), "No valid payment method found."

        token = transaction.payment_token_id

        # Reuse existing inactive group if one already exists for this token + partner
        existing_group = self.with_context(active_test=False).search([
            ('partner_id', '=', transaction.partner_id.id),
            ('payment_token_id', '=', token.id)
        ], limit=1)

        if existing_group:
            return existing_group, "This payment method was already saved."


        # 2. Identify Payment Mode from Token Name>
        # Strategy: The first part of the token name (before '_') is the method name (e.g. "MasterCard_123" -> "MasterCard")
        token_name_parts = token.name.split('_')
        method_name = token_name_parts[0].strip() if token_name_parts else token.name

        # Search for payment mode matching the brand name
        payment_mode = self.env['account.payment.mode'].sudo().search([
            ('name', 'ilike', method_name),
        ], limit=1)

        if not payment_mode:
            # Payment mode should have been validated to be used
            msg = "Unable to add the payment method."
            return self.browse(), msg

        # Construct Name/Ref
        ref = token.name

        vals = {
            'partner_id': transaction.partner_id.id,
            'payment_mode_id': payment_mode.id,
            'payment_token_id': token.id,
            'ref': ref,
            'active': True,
            'recurring_unit': 'month',
            'recurring_value': 1,
        }

        group = self.create(vals)
        return group, "Payment method added successfully."
