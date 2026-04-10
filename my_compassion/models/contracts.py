from odoo import fields, models


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
    )

    is_exit_communication_pending = fields.Boolean(
        string="Exit Communication Pending",
        compute="_compute_is_exit_communication_pending",
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

    def _compute_is_exit_communication_pending(self):
        # Fetch the XML IDs of the Planned and Unplanned Exit communication configs
        exit_configs = [
            self.env.ref(
                "partner_communication_compassion.lifecycle_child_planned_exit",
                raise_if_not_found=False,
            ),
            self.env.ref(
                "partner_communication_compassion.lifecycle_child_unplanned_exit",
                raise_if_not_found=False,
            ),
        ]
        config_ids = [c.id for c in exit_configs if c]

        for contract in self:
            if contract.state == "terminated" and config_ids:
                # Check if there is an unfinished communication job for this contract
                domain = [
                    ("config_id", "in", config_ids),
                    ("state", "in", ["pending", "processing", "failure"]),
                    ("object_ids", "=", str(contract.id)),
                ]
                pending_jobs = self.env["partner.communication.job"].search_count(
                    domain
                )
                contract.is_exit_communication_pending = pending_jobs > 0
            else:
                contract.is_exit_communication_pending = False
