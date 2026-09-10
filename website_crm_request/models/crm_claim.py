from odoo import models
from odoo.tools.mail import email_normalize


class CrmClaim(models.Model):
    _inherit = "crm.claim"

    def website_form_input_filter(self, request, values):
        """Attach the request to the contact that wrote it, creating one when
        no contact holds the address.
        """
        email = email_normalize(values.get("email_from") or "")
        if not email:
            return values

        params = request.params
        firstname = (params.get("firstname") or "").strip()
        lastname = (params.get("lastname") or "").strip()
        partner_obj = self.env["res.partner"].sudo()
        partner = partner_obj.search([("email", "=ilike", email)], limit=1)
        if not partner and (firstname or lastname):
            partner = (
                self.env["res.partner.match"]
                .sudo()
                ._create_partner(
                    {
                        "firstname": firstname,
                        "lastname": lastname,
                        "email": email,
                        "phone": values.get("partner_phone") or False,
                        "title": self._website_form_title(params.get("title")),
                    }
                )
            )

        if partner:
            values["partner_id"] = partner.id
            values["language"] = partner.lang
        return values

    def _website_form_title(self, shortcut):
        title_obj = self.env["res.partner.title"].sudo()
        return shortcut and title_obj.search([("shortcut", "=", shortcut)], limit=1).id
