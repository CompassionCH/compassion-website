# Class to add a registration edit form in MyCompassion
from odoo import api, fields, models


class RegistrationForm(models.TransientModel):
    _name = "event.registration.form"
    _description = "Event Registration Form (Edit)"

    registration_id = fields.Many2one("event.registration", required=True)
    profile_picture = fields.Binary(
        related="registration_id.profile_picture", readonly=False
    )
    profile_name = fields.Char(related="registration_id.profile_name", readonly=False)
    ambassador_quote = fields.Text(
        related="registration_id.ambassador_quote", readonly=False
    )
    receive_ambassador_receipts = fields.Boolean(
        related="registration_id.partner_id.receive_ambassador_receipts",
        readonly=False,
        default=False,
    )
    passport = fields.Binary(related="registration_id.passport", readonly=False)
    comments = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        forms = super().create(vals_list)
        for form in forms:
            if form.comments:
                form.registration_id.message_post(
                    body=form.comments,
                    author_id=form.registration_id.partner_id.id,
                    subtype_xmlid="mail.mt_comment",
                )
        return forms
