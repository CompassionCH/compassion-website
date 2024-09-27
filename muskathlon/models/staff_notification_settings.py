##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models


class StaffNotificationSettings(models.TransientModel):
    """Settings configuration for any Notifications."""

    _inherit = "res.config.settings"

    # Users to notify for Muskathlon Registration
    muskathlon_lead_notify_id = fields.Many2many(
        "res.users",
        string ="Muskathlon Registrations",
        domain=[("share", "=", False)],
        readonly=False,
        relation="muskathlon_lead_notify_rel",
    )
    muskathlon_order_notify_id = fields.Many2many(
        "res.users",
        string ="Muskathlon Material Orders",
        domain=[("share", "=", False)],
        readonly=False,
        relation="muskathlon_order_notify_rel",
    )

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "muskathlon.muskathlon_lead_notify_id",
            ",".join(map(str, self.muskathlon_lead_notify_id.ids)),
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "muskathlon.muskathlon_order_notify_id",
            ",".join(map(str, self.muskathlon_order_notify_id.ids)),
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()

        res.update(
            muskathlon_lead_notify_id=params.get_param("muskathlon.muskathlon_lead_notify_id", ""),
            muskathlon_order_notify_id=params.get_param("muskathlon.muskathlon_order_notify_id", ""),
        )
        if res['muskathlon_lead_notify_id']:
            res['muskathlon_lead_notify_id'] = [int(id) for id in res['muskathlon_lead_notify_id'].split(',') if
                                                id.isdigit()]
        if res['muskathlon_order_notify_id']:
            res['muskathlon_order_notify_id'] = [int(id) for id in res['muskathlon_order_notify_id'].split(',') if
                                                 id.isdigit()]
        return res
