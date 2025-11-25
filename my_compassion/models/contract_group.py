##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models, _


class ContractGroup(models.Model):
    _name = "recurring.contract.group"
    _inherit = ["recurring.contract.group", "translatable.model"]

    gender = fields.Selection(store=False)
    total_amount = fields.Float(compute="_compute_total_amount")

    def _compute_total_amount(self):
        for group in self:
            group.total_amount = sum(
                group.contract_ids.filtered(
                    lambda s: s.state not in ["terminated", "cancelled"]
                ).mapped("total_amount")
            )

    # TODO : Revise this method once final logic and needs are clarified
    def get_payment_method_info(self):
        """
        Returns a dict containing display info for the group's payment method.
        Used in MyCompassion2.0 portal.

        Logic:
        1. Get the Payment Mode from the group.
        2. Find the associated Payment Acquirer via fixed_journal_id from account.payment.mode
        3. Check if the partner has a saved Payment Token  for that Acquirer.
        """
        self.ensure_one()

        # Default / Fallback values
        info = {
            'icon_url': '/my_compassion/static/src/img/undefined.png',
            'label': _('Unknown Method'),
            'type': 'manual',  # 'manual', 'mode', or 'token'
            'brand': False,
            'mode_id': self.payment_mode_id.id if self.payment_mode_id else False
        }

        if not self.payment_mode_id:
            return info

        # 1. Basic Mode Info
        info['label'] = self.sudo().payment_mode_id.name
        info['type'] = 'mode'

        # 2. Resolve Acquirer via Journal (The link between Mode and Provider)
        # The 'fixed_journal_id' on payment mode usually points to the bank/provider journal
        journal_id = self.sudo().payment_mode_id.fixed_journal_id.id
        acquirer = False

        if journal_id:
            acquirer = self.env['payment.acquirer'].sudo().search([
                ('journal_id', '=', journal_id)
            ], limit=1)

        if acquirer:
            # 3. Find active Token (Saved Card) for this user + acquirer
            valid_token = self.env['payment.token'].sudo().search([
                ('partner_id', '=', self.partner_id.id),
                ('acquirer_id', '=', acquirer.id),
                # We usually want the default/active one. If multiple exist, taking the first is standard.
            ], limit=1)

            if valid_token:
                # We found a specific saved card
                info.update({
                    'icon_url': f'/my_compassion/static/src/img/{acquirer.id}/image_128',
                    'label': valid_token.name,
                    'type': 'token',
                    'token_id': valid_token.id,

                    'brand': valid_token.name.split(' ')[0] if valid_token.name else False
                })
            else:
                # We have an online provider (like Stripe) but no token found
                info.update({
                    'icon_url': f'/web/image/payment.acquirer/{acquirer.id}/image_128',
                    'label': acquirer.display_as or acquirer.name,
                })

        # 4. Special handling for offline methods (LSV / Direct Debit)
        elif 'LSV' in self.payment_mode_id.name or 'DD' in self.payment_mode_id.name:
            info['label'] = _('Direct Debit (LSV)')

        return info
