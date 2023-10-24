##############################################################################
#
#    Copyright (C) 2018 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json

from odoo import api, fields, models
from odoo.http import request

from odoo.addons.website.models.website import slugify as slug


class EventCompassion(models.Model):
    _name = "crm.event.compassion"
    _inherit = [
        "crm.event.compassion",
        "website.published.mixin",
        "translatable.model",
        "website.seo.metadata",
        "website.multi.mixin",
        "website.cover_properties.mixin",
    ]

    name = fields.Char(translate=True)
    website_description = fields.Html(translate=True, sanitize=False)
    website_intro = fields.Html(translate=True, sanitize=False)
    website_id = fields.Many2one("website", default=1)
    picture_1 = fields.Image("Banner image", attachment=True)
    website_image = fields.Char(compute="_compute_website_image")
    website_side_info = fields.Html(string="Side info", translate=True, sanitize=False)
    event_type_id = fields.Many2one(
        "event.type",
        "Registration Template",
        # Avoids selecting generic events
        domain=[("id", ">", 1)],
        readonly=False,
    )
    type = fields.Selection(default="meeting")
    odoo_event_id = fields.Many2one("event.event", readonly=False, ondelete="cascade")
    seats_expected = fields.Integer(related="odoo_event_id.seats_expected")
    registrations_ended = fields.Boolean(compute="_compute_registrations_ended")
    registration_ids = fields.One2many(
        "event.registration",
        "compassion_event_id",
        "Event registrations",
        readonly=False,
    )
    amount_objective = fields.Monetary(compute="_compute_amount_raised")
    amount_raised = fields.Monetary(compute="_compute_amount_raised")
    amount_raised_percents = fields.Monetary(compute="_compute_amount_raised")

    def _compute_registrations_ended(self):
        for event in self:
            event.registrations_ended = fields.Datetime.now() > event.end_date

    def _compute_website_url(self):
        for event in self:
            event.website_url = f"/event/{slug(event)}"

    def _compute_website_image(self):
        for event in self:
            event.website_image = request.website.image_url(
                event, "picture_1", size=self.env.context.get("image_size")
            )

    def _default_website_meta(self):
        default_meta = super()._default_website_meta()
        default_meta["default_opengraph"].update(
            {
                "og:image": self.website_image,
            }
        )
        default_meta["default_twitter"].update(
            {"twitter:image": self.with_context(image_size="300x300").website_image}
        )
        return default_meta

    def _compute_amount_raised(self):
        for event in self:
            amount_raised = 0
            amount_objective = 0

            for registration in event.sudo().registration_ids.filtered(
                lambda r: r.state != "cancel"
            ):
                amount_raised += registration.amount_raised
                amount_objective += registration.amount_objective

            event.amount_raised = amount_raised
            event.amount_objective = amount_objective
            event.amount_raised_percents = int(
                amount_raised * 100 / (amount_objective or 1)
            )

    def open_registrations(self):
        """
        This will create an event.event record and link it to the Compassion
        Event. It's useful for adding participants and managing e-mails
        and participant list.
        :return: action opening the wizard
        """
        if not self.odoo_event_id:
            return {
                "name": "Open event registrations",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "crm.event.compassion.open.wizard",
                "context": self.env.context,
                "target": "new",
            }

    def open_participants(self):
        return {
            "name": "Manage participants",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,tree,form,calendar,graph",
            "res_model": "event.registration",
            "domain": [("event_id", "=", self.odoo_event_id.id)],
            "context": self.with_context(
                default_compassion_event_id=self.id,
                default_event_type_id=self.event_type_id.id,
                default_event_id=self.odoo_event_id.id,
                default_amount_objective=self.odoo_event_id.participants_amount_objective,
            ).env.context,
            "target": "current",
        }

    def manage_event_registration(self):
        return {
            "name": "Manage event registration",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "event.event",
            "res_id": self.odoo_event_id.id,
        }

    @api.model
    def past_event_action(self):
        """Switch partners to "attended" after the event ended"""
        for event in self:
            if event.registrations_ended:
                participants = self.env["event.registration"].search(
                    [("event_id", "=", event.odoo_event_id.id)]
                )
                participants.past_event_action()

    def write(self, vals):
        if vals.get("picture_1"):
            vals["cover_properties"] = json.dumps(
                {
                    "background_image": vals["picture_1"],
                }
            )
        return super().write(vals)
