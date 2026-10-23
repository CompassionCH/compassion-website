##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models
from odoo.exceptions import AccessError

# Published records of these models must not be served by website's shortcut
# that hands any of their binary fields to anyone (T3569).
SHORTCUT_DENIED_MODELS = ("correspondence", "event.registration", "res.partner")


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field):
        if record._name in SHORTCUT_DENIED_MODELS:
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
