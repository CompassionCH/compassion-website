##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import logging

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.http import request
from odoo.tools import index_exists
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.website.models.website import slugify as slug

_logger = logging.getLogger(__name__)


class EventRegistration(models.Model):
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
        "event.registration",
        "mail.activity.mixin",
        "website.multi.mixin",
        "cms.form.partner",
        "translatable.model",
    ]
    _name = "event.registration"

    ##########################################################################
    #                                 FIELDS                                 #
    ##########################################################################
    down_payment_id = fields.Many2one(
        "account.move",
        string="Down Payment",
        readonly=False,
        related="sale_order_line_id.invoice_lines.move_id",
    )
    down_payment_link = fields.Char(compute="_compute_down_payment_link")
    trip_invoice_id = fields.Many2one(
        "account.move",
        "Trip invoice",
    )
    payment_link = fields.Char(compute="_compute_payment_link")
    single_room = fields.Boolean(help="The participant wants a single room")
    # Change readonly attribute so that form creation is possible
    event_id = fields.Many2one(
        readonly=False,
        states={
            "open": [("readonly", True)],
            "cancel": [("readonly", True)],
            "done": [("readonly", True)],
        },
    )
    company_id = fields.Many2one(related="event_id.company_id")
    user_id = fields.Many2one(
        "res.users",
        "Responsible",
        domain=[("share", "=", False)],
        tracking=True,
        readonly=False,
    )
    stage_id = fields.Many2one(
        "event.registration.stage",
        "Stage",
        tracking=True,
        index=True,
        copy=False,
        domain="['|', ('event_type_ids', '=', False),"
        "      ('event_type_ids', '=', event_type_id)]",
        group_expand="_read_group_stage_ids",
        default=lambda r: r._default_stage(),
        readonly=False,
    )
    stage_date = fields.Date(default=fields.Date.today, copy=False)
    task_ids = fields.One2many(
        "event.registration.task.rel",
        "registration_id",
        copy=False,
        readonly=False,
    )
    flight_ids = fields.One2many(
        "event.flight", "registration_id", "Flights", readonly=False
    )
    incomplete_task_count = fields.Integer(compute="_compute_incomplete_task_count")
    is_stage_complete = fields.Boolean(compute="_compute_is_stage_complete")
    compassion_event_id = fields.Many2one(
        "crm.event.compassion", related="event_id.compassion_event_id", readonly=True
    )
    fundraising = fields.Boolean(related="event_id.fundraising")
    amount_objective = fields.Monetary("Raise objective")
    amount_raised = fields.Monetary(readonly=True, compute="_compute_amount_raised")
    amount_raised_percents = fields.Integer(
        readonly=True, compute="_compute_amount_raised_percent"
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    is_published = fields.Boolean(compute="_compute_is_published", store=True)
    host_url = fields.Char(compute="_compute_host_url")
    sponsorship_url = fields.Char(compute="_compute_sponsorship_url")
    event_name = fields.Char(related="event_id.name", tracking=True)
    profile_picture = fields.Binary(readonly=False, string="Profile picture")
    profile_name = fields.Char()
    ambassador_quote = fields.Text()
    criminal_record = fields.Binary(
        related="partner_id.criminal_record", readonly=False
    )
    medical_survey_id = fields.Many2one(
        "survey.user_input", "Medical survey", compute="_compute_surveys"
    )
    feedback_survey_id = fields.Many2one(
        "survey.user_input", "Feedback survey", compute="_compute_surveys"
    )

    # Travel info
    #############
    emergency_name = fields.Char("Emergency contact name")
    emergency_phone = fields.Char("Emergency contact phone number")
    emergency_relation_type = fields.Selection(
        [
            ("husband", "Husband"),
            ("wife", "Wife"),
            ("father", "Father"),
            ("mother", "Mother"),
            ("brother", "Brother"),
            ("sister", "Sister"),
            ("son", "Son"),
            ("daughter", "Daughter"),
            ("friend", "Friend"),
            ("other", "Other"),
        ],
        string="Emergency contact relation type",
    )
    birth_name = fields.Char()
    passport = fields.Binary(compute="_compute_passport", inverse="_inverse_passport")
    passport_number = fields.Char()
    passport_filename = fields.Char(compute="_compute_passport")
    passport_expiration_date = fields.Date()
    survey_count = fields.Integer(compute="_compute_survey_count")
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    website_id = fields.Many2one(
        "website", related="compassion_event_id.website_id", store=True
    )

    def _auto_init(self):
        """This will speedup barometer computations"""
        super()._auto_init()
        if not index_exists(self.env.cr, "index_user_payment_event_contract"):
            self.env.cr.execute(
                """
                CREATE INDEX index_user_payment_event_contract
                ON account_move_line (user_id, payment_state, event_id, contract_id)"""
            )

    ##########################################################################
    #                             FIELDS METHODS                             #
    ##########################################################################
    def _compute_website_url(self):
        for registration in self:
            registration.website_url = "/event/{}/{}".format(
                slug(registration.compassion_event_id), slug(registration)
            )

    def _compute_amount_raised_percent(self):
        for registration in self:
            objective = (
                registration.amount_objective
                or registration.event_id.participants_amount_objective
            )
            if objective:
                registration.amount_raised_percents = int(
                    registration.amount_raised * 100 // objective
                )
            else:
                registration.amount_raised_percents = 0

    def _compute_amount_raised(self):
        for registration in self:
            partner = registration.partner_id
            compassion_event = registration.compassion_event_id
            invoice_lines = (
                self.env["account.move.line"]
                .sudo()
                .search(
                    [
                        ("user_id", "=", partner.id),
                        ("payment_state", "=", "paid"),
                        ("event_id", "=", compassion_event.id),
                        ("contract_id", "=", False),
                    ]
                )
            )
            amount_raised = sum(invoice_lines.mapped("price_subtotal"))
            s_value = registration.event_id.sponsorship_donation_value
            if s_value:
                nb_sponsorships = (
                    self.env["recurring.contract"]
                    .sudo()
                    .search_count(
                        [
                            ("ambassador_id", "=", partner.id),
                            ("origin_id.event_id", "=", compassion_event.id),
                            ("state", "!=", "cancelled"),
                        ]
                    )
                )
                amount_raised += nb_sponsorships * s_value
            registration.amount_raised = amount_raised

    def _compute_host_url(self):
        params_obj = self.env["ir.config_parameter"].sudo()
        host = params_obj.get_param("web.external.url") or params_obj.get_param(
            "web.base.url"
        )
        for registration in self:
            registration.host_url = host

    @api.depends("state")
    def _compute_is_published(self):
        for registration in self:
            registration.is_published = registration.state in ("open", "done")

    def _create_payment_link(self, move, description):
        payment_link = (
            request.env["payment.link.wizard"]
            .sudo()
            .create(
                {
                    "res_id": move.id,
                    "res_model": "account.move",
                    "amount": move.amount_residual,
                    "currency_id": move.currency_id.id,
                    "partner_id": move.partner_id.id,
                    "amount_max": move.amount_residual,
                    "description": description,
                }
            )
        )
        return payment_link.link

    def _compute_down_payment_link(self):
        for registration in self:
            if registration.down_payment_id:
                move = registration.down_payment_id
                description = (
                    _("Down payment for %s") % registration.compassion_event_id.name
                )
                registration.down_payment_link = (
                    self._create_payment_link(move, description)
                    + f"&return_url=/my/events/{registration.id}"
                )
            else:
                registration.down_payment_link = False

    def _compute_payment_link(self):
        for registration in self:
            if registration.trip_invoice_id:
                move = registration.trip_invoice_id
                description = (
                    _("Payment for %s") % registration.compassion_event_id.name
                )
                registration.payment_link = (
                    self._create_payment_link(move, description)
                    + f"&return_url=/my/events/{registration.id}"
                )
            else:
                registration.payment_link = False

    def _default_website_meta(self):
        default_meta = super()._default_website_meta()
        company = request.website.company_id.sudo()
        website_name = (request.website or company).name
        title = f"{self.profile_name} - {self.event_name} | {website_name}"
        default_meta["default_opengraph"].update(
            {
                "og:title": title,
                "og:image": request.website.image_url(self, "profile_picture"),
            }
        )
        default_meta["default_twitter"].update(
            {
                "twitter:title": title,
                "twitter:image": request.website.image_url(
                    self, "profile_picture", size="300x300"
                ),
            }
        )
        default_meta.update(
            {
                "default_meta_description": self._get_default_meta_description(),
            }
        )
        return default_meta

    def _get_default_meta_description(self):
        return self.ambassador_quote or _(
            "Join me in my efforts to release children from poverty in Jesus' name!"
        )

    def _compute_sponsorship_url(self):
        for registration in self:
            registration.sponsorship_url = (
                f"/children?registration_id={registration.id}"
            )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # retrieve event type from the context and write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        type_id = self._context.get("default_event_type_id")
        search_domain = [
            ("event_type_ids", "=", type_id),
        ]
        if stages:
            search_domain = ["|", ("id", "in", stages.ids)] + search_domain

        # perform search
        stage_ids = stages._search(
            search_domain, order=order, access_rights_uid=SUPERUSER_ID
        )
        return stages.browse(stage_ids)

    @api.model
    def _default_stage(self):
        type_id = self._context.get("default_event_type_id")
        if type_id:
            stage = self.env["event.registration.stage"].search(
                ["|", ("event_type_ids", "=", type_id), ("event_type_ids", "=", False)],
                limit=1,
            )
        else:
            stage = self.env["event.registration.stage"].search(
                [("event_type_ids", "=", False)], limit=1
            )
        return stage.id

    def _compute_incomplete_task_count(self):
        for registration in self:
            registration.incomplete_task_count = len(
                registration.task_ids.filtered(
                    lambda t: t.task_id.website_published and not t.done
                )
            )

    def _compute_is_stage_complete(self):
        for registration in self:
            incomplete_tasks = registration.task_ids.filtered(
                lambda t, r=registration: t.stage_id == r.stage_id and not t.done
            )
            registration.is_stage_complete = not incomplete_tasks

    def _compute_tasks(self):
        # Add tasks for the current stage
        for registration in self:
            missing_tasks = registration.stage_id.task_ids - registration.mapped(
                "task_ids.task_id"
            )
            if missing_tasks:
                registration.task_ids += self.env["event.registration.task.rel"].create(
                    [
                        {"task_id": task.id, "registration_id": registration.id}
                        for task in missing_tasks
                    ]
                )

    def _compute_survey_count(self):
        for registration in self:
            event = registration.event_id
            surveys = event.medical_survey_id + event.feedback_survey_id
            registration.survey_count = self.env["survey.user_input"].search_count(
                [
                    ("partner_id", "=", registration.partner_id.id),
                    ("survey_id", "in", surveys.ids),
                ]
            )

    def _compute_invoice_count(self):
        for registration in self:
            event = registration.compassion_event_id
            registration.invoice_count = self.env["account.move"].search_count(
                [
                    ("line_ids.event_id", "=", event.id),
                    ("line_ids.user_id", "=", registration.partner_id.id),
                    ("invoice_category", "!=", "sponsorship"),
                ]
            )

    def _compute_passport(self):
        for registration in self:
            attachment = self.env["ir.attachment"].search(
                [
                    ("name", "like", "Passport"),
                    ("res_id", "=", registration.id),
                    ("res_model", "=", self._name),
                ],
                limit=1,
            )
            registration.passport = attachment.datas
            registration.passport_filename = attachment.name

    def _inverse_passport(self):
        attachment_obj = self.env["ir.attachment"].sudo()
        for registration in self:
            passport = registration.passport
            if passport:
                f_type = guess_mimetype(base64.decodebytes(passport), "/pdf").split(
                    "/"
                )[1]
                name = f"Passport {registration.name}.{f_type}"
                attachment_obj.create(
                    {
                        "res_model": self._name,
                        "res_id": registration.id,
                        "datas": passport,
                        "name": name,
                    }
                )
            else:
                attachment_obj.search(
                    [
                        ("name", "like", "Passport"),
                        ("res_id", "=", registration.id),
                        ("res_model", "=", self._name),
                    ]
                ).unlink()

    def _compute_surveys(self):
        user_input_obj = self.env["survey.user_input"]
        for registration in self:
            medical_survey = registration.event_id.medical_survey_id
            feedback_survey = registration.event_id.feedback_survey_id
            registration.medical_survey_id = user_input_obj.search(
                [
                    ("survey_id", "=", medical_survey.id),
                    ("partner_id", "=", registration.partner_id.id),
                ],
                order="start_datetime desc",
                limit=1,
            )
            registration.feedback_survey_id = user_input_obj.search(
                [
                    ("survey_id", "=", feedback_survey.id),
                    ("partner_id", "=", registration.partner_id.id),
                ],
                order="start_datetime desc",
                limit=1,
            )

    def _notify_get_action_link(self, link_type, **kwargs):
        # Avoids the notifications to point to website url
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        link = super()._notify_get_action_link(link_type, **kwargs)
        return link.replace(self.get_base_url(), base_url)

    ##########################################################################
    #                              ORM METHODS                               #
    ##########################################################################
    def write(self, vals):
        if "stage_id" in vals:
            vals["stage_date"] = fields.Date.today()
            if "state" not in vals:
                stage = self.env["event.registration.stage"].browse(vals["stage_id"])
                if stage.registration_state:
                    vals["state"] = stage.registration_state
        super().write(vals)
        if "stage_id" in vals:
            self._compute_tasks()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for registration in records:
            # Copy image fields
            if registration.profile_picture:
                registration.partner_id.image_1920 = registration.profile_picture
            if not registration.profile_name:
                registration.profile_name = registration.partner_id.preferred_name
            # Set default fundraising objective if none was set
            event = records.event_id
            if (
                not registration.amount_objective
                and event.participants_amount_objective
            ):
                registration.amount_objective = event.participants_amount_objective
            # Set donation receipt preference
            registration.partner_id.receive_ambassador_receipts = True

        # check the subtype note by default
        # for all the default follower of a new registration
        records.mapped("message_follower_ids").write(
            {"subtype_ids": [(4, self.env.ref("mail.mt_note").id)]}
        )

        # Automatically compute tasks and change stage if tasks are good
        records._compute_tasks()
        records.next_stage()
        return records

    ##########################################################################
    #                             PUBLIC METHODS                             #
    ##########################################################################
    def button_send_reminder(self):
        """Create a communication job with a chosen communication config"""

        ctx = {"partner_id": self.partner_id.id, "object_ids": self.ids}

        return {
            "name": _("Choose a communication"),
            "type": "ir.actions.act_window",
            "res_model": "event.registration.communication.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def send_communication(
        self,
        config_id,
        force_send=False,
        filter_func=lambda self: self.state != "cancel",
    ):
        """
        Send a communication rule to all attendees of the event
        @param config_id: communication config id
        @param force_send: if True, send the communication immediately regardless
                           of its send_mode
        @param filter_func: filter function to apply on the registrations
        @return: communication jobs
        """
        communications = self.env["partner.communication.job"].create(
            [
                {
                    "config_id": config_id,
                    "partner_id": registration.partner_id.id,
                    "object_ids": [registration.id],
                }
                for registration in self.filtered(filter_func)
            ]
        )
        if force_send:
            communications.send()
        return communications

    def action_set_done(self):
        super().action_set_done()
        return self.write(
            {"stage_id": self.env.ref("website_event_compassion.stage_all_attended").id}
        )

    def action_cancel(self):
        super().action_cancel()
        return self.write(
            {
                "stage_id": self.env.ref(
                    "website_event_compassion.stage_all_cancelled"
                ).id
            }
        )

    def get_event_registration_survey(self):
        event = self.event_id
        surveys = event.medical_survey_id + event.feedback_survey_id
        return {
            "type": "ir.actions.act_window",
            "res_model": "survey.user_input",
            "name": _("Surveys"),
            "view_mode": "tree,form",
            "domain": [
                ("survey_id", "in", surveys.ids),
                ("partner_id", "=", self.partner_id.id),
            ],
            "context": self.env.context,
        }

    def show_invoice(self):
        return {
            "name": _("Donations"),
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "account.move",
            "context": self.env.context,
            "domain": [
                ("line_ids.event_id", "=", self.compassion_event_id.id),
                ("line_ids.user_id", "=", self.partner_id.id),
                ("invoice_category", "!=", "sponsorship"),
            ],
        }

    def create_down_payment(self):
        down_payment_product = self.env.ref("event_sale.product_product_event")
        for registration in self:
            ticket = registration.event_id.event_ticket_ids.filtered(
                lambda t: t.product_id == down_payment_product
            )
            if ticket and not self.down_payment_id:
                order = self.env["sale.order"].create(
                    {
                        "partner_id": registration.partner_id.id,
                        "order_line": [
                            (
                                0,
                                0,
                                {
                                    "product_id": down_payment_product.id,
                                    "name": ticket.name,
                                    "price_unit": ticket.price,
                                    "product_uom_qty": 1,
                                    "registration_id": registration.id,
                                },
                            )
                        ],
                    }
                )
                order.order_line[0].event_id = registration.event_id.id

                registration.write(
                    {
                        "sale_order_id": order.id,
                        "sale_order_line_id": order.order_line[0].id,
                    }
                )

                order.action_confirm()

                registration.write({"event_ticket_id": ticket.id})
        return True

    def create_trip_invoice(self):
        travel_cost = self.env.ref(
            "website_event_compassion.product_template_trip_price"
        )
        single_room_cost = self.env.ref(
            "website_event_compassion.product_template_single_room"
        )
        sales_journal = self.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        for registration in self:
            travel_ticket = registration.event_id.event_ticket_ids.filtered(
                lambda t, template=travel_cost: t.product_id.product_tmpl_id == template
            )
            if len(travel_ticket) > 1:
                # Take the price set at the date of registration
                travel_ticket = travel_ticket.filtered(
                    lambda t, reg=registration: (
                        t.start_sale_date or reg.create_date.date()
                    )
                    <= reg.create_date.date()
                    <= (t.end_sale_date or reg.create_date.date())
                )[:1]
            room_ticket = registration.event_id.event_ticket_ids.filtered(
                lambda t: t.product_id.product_tmpl_id == single_room_cost
            )
            if travel_ticket and not registration.trip_invoice_id:
                product = travel_ticket.product_id
                invoice_lines = [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "account_id": product.property_account_income_id.id,
                            "name": travel_ticket.name,
                            "price_unit": travel_ticket.price,
                            "quantity": 1,
                        },
                    ),
                ]
                if registration.single_room and room_ticket:
                    product = room_ticket.product_id
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "account_id": product.property_account_income_id.id,
                                "name": room_ticket.name,
                                "price_unit": room_ticket.price,
                                "quantity": 1,
                            },
                        ),
                    )
                registration.trip_invoice_id = self.env["account.move"].create(
                    {
                        "partner_id": registration.partner_id.id,
                        "move_type": "out_invoice",
                        "journal_id": sales_journal.id,
                        "invoice_date": fields.Date.today(),
                        "invoice_line_ids": invoice_lines,
                    }
                )
                registration.trip_invoice_id.action_post()
        return True

    ##########################################################################
    #                       STAGE TRANSITION METHODS                         #
    ##########################################################################

    def next_stage(self):
        """Transition to next registration stage"""
        stage_complete = self.filtered("is_stage_complete")
        for registration in stage_complete:
            next_stage = self.env["event.registration.stage"].search(
                [
                    ("sequence", ">", registration.stage_id.sequence),
                    "|",
                    ("event_type_ids", "in", registration.stage_id.event_type_ids.ids),
                    ("event_type_ids", "=", False),
                ],
                limit=1,
            )
            if next_stage:
                registration.write({"stage_id": next_stage.id})

        # Send potential communications after stage transition
        if stage_complete:
            self.env["event.mail"].with_delay().run()
        return True

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "user_id" in init_values and init_values["user_id"] is False:
            # When the registration is created.
            return "website_event_compassion.mt_registration_create"
        return super()._track_subtype(init_values)

    def past_event_action(self):
        attended = self.env.ref("website_event_compassion.stage_all_attended")
        cancel = self.env.ref("website_event_compassion.stage_all_cancelled")
        for reg in self:
            if reg.state == "open":
                reg.stage_id = attended
            elif reg.state == "draft":
                reg.stage_id = cancel
        # Destroy sensitive data
        self.mapped("medical_survey_id").unlink()
