from odoo import fields, models


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
