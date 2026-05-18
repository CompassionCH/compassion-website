from odoo import fields, models


class RecurringContract(models.Model):
    """
    Extends the recurring.contract model for MyCompassion features.

    Inheriting "utm.mixin" makes sure that the model integrates Odoo's utm features.
    This allows Odoo to automatically intercept UTM cookies.
    """

    _name = "recurring.contract"
    _inherit = ["recurring.contract", "utm.mixin"]

    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
    )

    def _compute_can_show_on_my_compassion(self):
        """
        Return if a contract is active or terminated,
        or if the contract is new (not cancelled and without parent)
        """
        for contract in self:
            contract.can_show_on_my_compassion = contract.state in [
                "active",
                "terminated",
            ] or (contract.state != "cancelled" and not contract.parent_id)
