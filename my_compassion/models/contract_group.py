##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from urllib.parse import parse_qs, urlparse

from odoo import _, api, fields, models


class ContractGroup(models.Model):
    _name = "recurring.contract.group"
    _inherit = ["recurring.contract.group", "translatable.model"]

    active = fields.Boolean(default=True)
    payment_token_id = fields.Many2one("payment.token", string="Payment Token")
    gender = fields.Selection(related="partner_id.gender", store=True, readonly=True)
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
        Returns a dictionary mapping group IDs to their payment method info.
        The info includes icon ID, reference number, label, expiration date,
        whether it's a card, payment mode ID, and group ID.
        """
        # 1. Prefetch all icons to avoid N+1 queries
        all_icons = self.env["payment.icon"].sudo().search([("image", "!=", False)])

        result_map = {}

        for group in self:
            info = {
                "icon": False,
                "ref_number": False,
                "label": _("Unknown Method"),
                "expire_date": False,
                "is_card": False,
                "mode_id": group.payment_mode_id.id if group.payment_mode_id else False,
                "group_id": group.id,
            }

            search_term = False

            # Logic: Online Token
            if group.payment_token_id:
                info["is_card"] = True
                token_name = group.payment_token_id.name or ""
                brand_name = token_name.split("_")[0] if "_" in token_name else token_name
                info["label"] = brand_name
                search_term = brand_name

            # Logic: Manual Mode
            elif group.payment_mode_id:
                info["type"] = "mode"
                info["label"] = group.payment_mode_id.name
                if group.bvr_reference:
                    info["ref_number"] = group.bvr_reference
                search_term = group.payment_mode_id.name

            # Icon Lookup (In-Memory)
            if search_term:
                found_icon = all_icons.filtered(
                    lambda i: i.name.lower() == search_term.lower() or search_term.lower() in i.name.lower()
                )
                if found_icon:
                    info["icon"] = found_icon[0].id

            result_map[group.id] = info

        return result_map

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

    @api.model
    def create_from_transaction(self, tx):
        """
        Creates or retrieves a contract group from a validation transaction.
        :param tx: payment.transaction record
        :return: (group_record, message_string)
        """
        if not tx or not tx.payment_token_id:
            return {
                "group": self.browse(),
                "status": "error",
                "message": _("No valid payment method found."),
            }
        token = tx.payment_token_id

        # 1. Reuse existing group (Idempotency)
        existing_group = self.with_context(active_test=False).search(
            [
                ("partner_id", "=", tx.partner_id.id),
                ("payment_token_id", "=", token.id),
            ],
            limit=1,
        )

        if existing_group:
            # Reactivate if it was archived
            if not existing_group.active:
                existing_group.active = True
            return {
                "group": existing_group,
                "status": "existing",
                "message": _("This payment method was already saved."),
            }
        # 2. Retrieve Recurring Frequency (Unit/Value)
        # Default to monthly if not specified
        recurring_unit = "month"
        recurring_value = 1

        if tx.return_url:
            try:
                parsed = urlparse(tx.return_url)
                params = parse_qs(parsed.query)
                if "unit" in params:
                    recurring_unit = params["unit"][0]
                if "val" in params:
                    recurring_value = int(params["val"][0])
                # Clean up URL params

            except (ValueError, KeyError):
                pass

        # 3. Identify Payment Mode
        company_id = tx.acquirer_id.company_id.id
        domain = [
            ("company_id", "=", company_id),
            ("payment_type", "=", "inbound"),
        ]

        payment_mode = False

        # Use token name to find matching mode
        payment_brand = (
            token.name.split("_")[0] if token.name and "_" in token.name else token.name
        )
        if payment_brand:
            payment_mode = self.env["account.payment.mode"].search(
                domain + [("name", "ilike", "%" + payment_brand + "%")], limit=1
            )

        # Fallback to Acquirer's Journal (Standard Odoo Link)
        if not payment_mode and tx.acquirer_id and tx.acquirer_id.journal_id:
            payment_mode = self.env["account.payment.mode"].search(
                domain + [("fixed_journal_id", "=", tx.acquirer_id.journal_id.id)],
                limit=1,
            )

        if not payment_mode:
            return self.browse(), _(
                "Configuration Error: No suitable electronic payment mode found."
            )

        # 4. Create the Group
        vals = {
            "partner_id": tx.partner_id.id,
            "payment_mode_id": payment_mode.id,
            "payment_token_id": token.id,
            "recurring_unit": recurring_unit,
            "recurring_value": recurring_value,
            "active": True,
            "ref": token.name,
        }

        group = self.create(vals)
        return {
            "group": group,
            "status": "new",
            "message": _("Payment method successfully added."),
        }

    # save icons to not reload them each time
    def get_payment_method_icons(self):
        """Returns a dictionary of payment method icons for quick access."""
        icons = {}
        icon_records = (
            self.env["payment.icon"]
            .sudo()
            .search([("image", "!=", False)])
        )
        for icon in icon_records:
            icons[icon.name.lower()] = icon.id
        return icons