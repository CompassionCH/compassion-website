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
        self.is_exit_communication_pending = False

        # Fetch the XML IDs of the Planned and Unplanned Exit configs
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

        # Isolate only the contracts that need to be checked
        terminated_contracts = self.filtered(lambda c: c.state == "terminated")

        if config_ids and terminated_contracts:
            domain = [
                ("config_id", "in", config_ids),
                ("state", "in", ["pending", "processing", "failure"]),
            ]

            # request only object_ids column
            pending_jobs = self.env["partner.communication.job"].search_read(
                domain, ["object_ids"]
            )

            # Parse the comma-separated strings into a flat set of individual IDs
            pending_contract_ids = set()
            for job in pending_jobs:
                if job.get("object_ids"):
                    job_ids = [i.strip() for i in job["object_ids"].split(",")]
                    pending_contract_ids.update(job_ids)

            for contract in terminated_contracts:
                if str(contract.id) in pending_contract_ids:
                    contract.is_exit_communication_pending = True
