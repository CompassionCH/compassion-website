##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import fields, models
from odoo.exceptions import AccessError

# Published records whose pictures are private too (T3569). Registration
# photos have their own route, /event/registration/<id>/photo.
SHORTCUT_DENIED_MODELS = (
    "correspondence",
    "event.registration",
    "res.partner",
    "res.users",
)


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        # website serves any binary field of a published record to anyone. Keep
        # that for pictures only: documents (passports, letter scans...) and the
        # models above go through the normal access check (T3569).
        if (
            "website_published" in record._fields
            and record.sudo().website_published
            and (
                record._name in SHORTCUT_DENIED_MODELS
                or not isinstance(record._fields.get(field), fields.Image)
            )
        ):
            record.check_access("read")
            return record
        return super()._find_record_check_access(record, access_token, field)

    def _get_stream_from(
        self,
        record,
        field_name="raw",
        filename=None,
        filename_field="name",
        mimetype=None,
        default_mimetype="application/octet-stream",
    ):
        # The record may come sudo-ed from website's published shortcut, which
        # would let ?filename_field= read any of its fields (T3569).
        if (
            filename_field
            and record.env.su
            and not self.env.su
            and record._name != "ir.attachment"
            and filename_field in record._fields
        ):
            visitor_record = record.with_env(self.env)
            try:
                visitor_record.check_access("read")
                visitor_record.check_field_access_rights("read", [filename_field])
            except AccessError:
                filename_field = ""
        return super()._get_stream_from(
            record, field_name, filename, filename_field, mimetype, default_mimetype
        )
