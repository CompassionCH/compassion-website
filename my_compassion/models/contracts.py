from odoo import fields, models, _
from odoo.exceptions import UserError


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
    )

    def _compute_can_show_on_my_compassion(self):
        for contract in self:
            contract.can_show_on_my_compassion = contract.state in [
                "active",
                "terminated",
            ] or (contract.state != "cancelled" and not contract.parent_id)

    def change_contract_group(self, new_group_id):
        """
        Moves the sponsorship (self) to the specified contract group.
        :param new_group_id: int ID of the target recurring.contract.group
        """
        self.ensure_one()

        if not new_group_id:
            return False

        # If we are already in this group, do nothing
        if self.group_id.id == new_group_id:
            return True

        target_group = self.env['recurring.contract.group'].browse(new_group_id)

        if not target_group.exists():
            return False

        # Move the contract to the new group
        old_group = self.group_id
        self.write({'group_id': target_group.id})

        return True