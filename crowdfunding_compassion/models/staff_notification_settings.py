from odoo import fields, models


class StaffNotificationSettings(models.TransientModel):
    """Settings configuration for any Notifications."""

    _inherit = "res.config.settings"

    new_participant_notify_ids = fields.Many2many(
        "res.partner",
        relation="res_config_settings_new_participant_notify_rel",
        string="New crowdfunding participant",
        domain=[("user_ids", "!=", False), ("user_ids.share", "=", False)],
        readonly=False,
    )

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "crowdfunding_compassion.new_participant_notify_ids",
            ",".join(list(map(str, self.new_participant_notify_ids.ids))),
        )

    def get_values(self):
        param_obj = self.env["ir.config_parameter"].sudo()
        res = super().get_values()
        res["new_participant_notify_ids"] = False
        partners = param_obj.get_param(
            "crowdfunding_compassion.new_participant_notify_ids", False
        )
        if partners:
            res["new_participant_notify_ids"] = [
                (6, 0, list(map(int, partners.split(","))))
            ]
        return res
