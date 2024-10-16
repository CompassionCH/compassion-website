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
    muskathlon_order_notify_id = fields.Many2one(
        "res.users",
        "Muskathlon Material Orders",
        domain=[("share", "=", False)],
        readonly=False,
    )

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "muskathlon.muskathlon_order_notify_id",
            str(self.muskathlon_order_notify_id.id),
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()

        res.update(
            muskathlon_order_notify_id=int(
                params.get_param("muskathlon.muskathlon_order_notify_id", 1)
            ),
        )
        return res
