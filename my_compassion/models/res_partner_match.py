from odoo import api, models


class PartnerMatch(models.AbstractModel):
    _inherit = "res.partner.match"

    def _get_valid_update_fields(self):
        res = super()._get_valid_update_fields()
        res.extend(["birthdate_date", "spoken_lang_ids", "church_id"])
        return res

    def _get_valid_create_fields(self):
        res = super()._get_valid_create_fields()
        res.extend(["firstname", "lastname"])
        return res

    @api.model
    def _joined_name(self, vals):
        """The searchable name of vals, joined from its two name parts.

        Missing keys raise KeyError, which is what makes the callers below
        fall back to the parent's "name" rule. A key that is present but
        empty is a different case - a sponsor who gave only one of the two
        parts, or none at all under a deferred-details checkout - and must
        degrade to a shorter search or to that same fallback, never to a
        TypeError on a False operand.
        """
        name = f"{vals['firstname'] or ''} {vals['lastname'] or ''}".strip()
        if not name:
            raise KeyError("firstname")
        return name

    def _match_email_and_name(self, vals):
        # Replace the rule with fuzzy search and using firstname and lastname
        try:
            email = vals["email"].strip()
            name = self._joined_name(vals)
            return self.env["res.partner"].search(
                [
                    ("name", "%", name),
                    ("email", "=ilike", email),
                ],
                limit=1,
            )
        except KeyError:
            # No "firstname" or "lastname", the caller probably expected the initial
            # behavior of the parent with "name"
            return super()._match_email_and_name(vals)

    def _match_name_and_zip(self, vals):
        # Replace the rule for using firstname and lastname
        try:
            name = self._joined_name(vals)
            return self.env["res.partner"].search(
                [
                    ("name", "ilike", name),
                    ("zip", "=", vals["zip"]),
                ],
                limit=1,
            )
        except KeyError:
            # No "firstname" or "lastname", the caller probably expected the initial
            # behavior of the parent with "name"
            return super()._match_name_and_zip(vals)
