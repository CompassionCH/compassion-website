from odoo import models


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

    def _match_email_and_name(self, vals):
        # Replace the rule with fuzzy search and using firstname and lastname
        try:
            email = vals["email"].strip()
            name = vals["firstname"] + " " + vals["lastname"]
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
            name = vals["firstname"] + " " + vals["lastname"]
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
