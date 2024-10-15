##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#    @author: Sebastien Toth <popod@me.com>
#    @author: Nicolas Badoux <n.badoux@hotmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import _, api, fields, models


class EventCompassion(models.Model):
    _inherit = "crm.event.compassion"

    sport_discipline_ids = fields.Many2many(
        "sport.discipline", string="Sport disciplines", readonly=False
    )
    is_muskathlon = fields.Boolean(compute="_compute_is_muskathlon")

    # HTML fields for Muskathlon material order page
    website_my_introduction = fields.Html(
        string="Video introduction", translate=True, sanitize=False
    )
    website_my_fundraising = fields.Html(
        string="Fundraising", translate=True, sanitize=False
    )
    website_my_information = fields.Html(
        string="Event information", translate=True, sanitize=False
    )
    website_my_press_material = fields.Html(
        string="Press material", translate=True, sanitize=False
    )
    website_my_sport_material = fields.Html(
        string="Sport material", translate=True, sanitize=False
    )

    def _compute_is_muskathlon(self):
        for event in self:
            event.is_muskathlon = event.odoo_event_id.event_type_id == self.env.ref(
                "muskathlon.event_type_muskathlon"
            )

    @api.onchange("event_type_id")
    def onchange_event_type_id(self):
        super().onchange_event_type_id()
        if self.event_type_id == self.env.ref("muskathlon.event_type_muskathlon"):
            self.ambassador_config_id = self.env.ref(
                "muskathlon.ambassador_donation_confirmation_config"
            )
            self.ambassador_sponsorship_config_id = self.env.ref(
                "muskathlon.ambassador_sponsorship_notification_config"
            )

    @api.model
    def get_sport_levels(self):
        return [
            ("beginner", _("Beginner")),
            ("average", _("Average")),
            ("advanced", _("Advanced")),
        ]

    @api.model
    def get_t_shirt_sizes(self):
        return [
            ("S", _("S")),
            ("M", _("M")),
            ("L", _("L")),
            ("XL", _("XL")),
            ("XXL", _("XXL")),
        ]
