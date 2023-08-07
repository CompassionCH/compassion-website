##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WebsiteSponsorship(models.TransientModel):
    _name = "cms.form.sponsorship"
    _inherit = ["cms.form.partner", "utm.mixin"]
    _description = "Website sponsorship form"

    child_id = fields.Many2one("compassion.child", "Child", required=True)
    sponsorship_type = fields.Selection(
        [("S", "Regular"), ("SC", "Correspondence"), ("SWP", "Write&Pray")],
        default="S",
        required=True,
    )
    sponsorship_amount = fields.Selection(
        [("regular", "Regular sponsorship"), ("plus", "PLUS Sponsorship")],
        "Type of sponsorship",
        default="regular",
        required=True,
    )
    payment_mode_id = fields.Many2one("account.payment.mode", "Payment method")
    origin_id = fields.Many2one(
        "recurring.contract.origin",
        "Origin of my sponsorship",
        domain=[("website_published", "=", True)],
    )
    contract_id = fields.Many2one("recurring.contract")
    notes = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for form in records:
            if form.match_update:
                # This is Step2, Update the contract
                form.contract_id = self.env["recurring.contract"].search(
                    [
                        ("correspondent_id", "=", form.partner_id.id),
                        ("child_id", "=", form.child_id.id),
                        ("state", "=", "draft"),
                    ]
                )
                form.contract_id.write(form._get_sponsorship_vals())
            else:
                # This is Step1, Create the sponsorship
                if self.env["recurring.contract"].search_count(
                    [
                        ("child_id", "=", form.child_id.id),
                        ("state", "not in", ["terminated", "cancelled"]),
                    ]
                ):
                    raise UserError(_("Sorry, the child is no longer available."))
                form.contract_id = self.env["recurring.contract"].create(
                    form._get_sponsorship_vals()
                )
                privacy_statement = self.env["compassion.privacy.statement"].search(
                    [], limit=1
                )
                if privacy_statement:
                    self.env["privacy.statement.agreement"].create(
                        {
                            "partner_id": form.partner_id.id,
                            "agreement_date": datetime.today(),
                            "privacy_statement_id": privacy_statement.id,
                            "version": privacy_statement.version,
                            "origin_signature": "new_sponsorship",
                        }
                    )
        return records

    def write(self, vals):
        notes = vals.get("notes")
        if notes:
            self.mapped("contract_id").message_post(body=notes)
        return super().write(vals)

    def _get_sponsorship_vals(self):
        self.ensure_one()
        group = self.env["recurring.contract.group"].search(
            [
                ("payment_mode_id", "=", self.payment_mode_id.id),
                ("partner_id", "=", self.partner_id.id),
            ],
            limit=1,
        )
        if not group:
            group = group.create(
                [
                    {
                        "partner_id": self.partner_id.id,
                        "payment_mode_id": self.payment_mode_id.id,
                    }
                ]
            )
        lines = (
            self.env["recurring.contract"]
            .with_context(default_type="S")
            ._get_standard_lines()
        )
        if self.sponsorship_amount == "regular":
            # Remove the GEN Fund
            lines.pop()
        res = {
            "partner_id": self.partner_id.id,
            # We could later implement another correspondent selection
            "correspondent_id": self.partner_id.id,
            "child_id": self.child_id.id,
            "type": self.sponsorship_type,
            "group_id": group.id,
            "origin_id": self.origin_id.id,
            "contract_line_ids": lines,
        }
        res.update(self._get_utm_data())
        if self.contract_id:
            # Filter unchanged values
            c_vals = self.contract_id.read(res.keys())[0]
            write_blacklist = ["child_id", "partner_id", "correspondent_id", "type"]
            res = {
                key: val
                for key, val in res.items()
                if val != c_vals[key] and key not in write_blacklist
            }
        return res

    def _get_utm_data(self):
        # This will read what is stored in the cookie. Can be inherited
        # if custom behaviour is needed.
        res = self.default_get(["medium_id", "source_id", "campaign_id"])
        if "medium_id" not in res:
            res["medium_id"] = self.env.ref("utm.utm_medium_website").id
        return res
