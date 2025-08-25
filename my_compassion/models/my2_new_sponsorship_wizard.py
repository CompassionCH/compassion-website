from odoo import fields, models


class NewSponsorshipWizard(models.TransientModel):
    _name = "new.sponsorship.wizard"
    _description = "New Sponsorship Wizard"

    n_steps = 3
    step = fields.Integer()

    child = fields.Many2one("compassion.child")

    # User details fields
    title = fields.Many2one("res.partner.title")
    lastname = fields.Char()
    firstname = fields.Char()
    birthdate = fields.Date()
    email = fields.Char()
    phone = fields.Char()
    street = fields.Char()
    street_number = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    country = fields.Many2one("res.country")

    # Payment fields
    payment_method = fields.Many2one(
        "account.payment.mode",
        # TODO: decide if we use website_published or not
        # domain=[("website_published", "=", True)],
    )
    sponsorship_plus = fields.Boolean()

    # Communication fields
    spoken_languages = fields.Many2many(
        "res.lang.compassion",
        domain=[("translatable", "=", True)],
    )
    lead_source = fields.Many2one(
        "recurring.contract.origin",
        # TODO: decide if we use website_published or not
        # domain=[("website_published", "=", True)],
    )
    volunteering = fields.Boolean()

    def action_next_step(self):
        self.ensure_one()
        if self.step < (self.n_steps - 1):
            self.step += 1

    def action_previous_step(self):
        self.ensure_one()
        if self.step > 0:
            self.step -= 1

    def action_finish_sponsorship(self):
        self.ensure_one()

        # Look for existing partner, create one if not found
        partner_vals = {
            "title": self.title.id,
            "lastname": self.lastname,
            "firstname": self.firstname,
            "birthdate_date": self.birthdate,
            "email": self.email,
            "phone": self.phone,
            "street": f"{self.street} {self.street_number}",
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country.id,
            "spoken_lang_ids": [(4, lang.id) for lang in self.spoken_languages],
            "interested_for_volunteering": self.volunteering,
        }
        partner = self.env["res.partner.match"].match_values_to_partner(
            partner_vals, match_update=False, match_create=False
        )
        if not partner:
            partner = self.env["res.partner"].create(partner_vals)

        # Create new sponsorship
        sponsorship = self.env["recurring.contract"].create(
            {
                "partner_id": partner.id,
                "child_id": self.child.id,
                "payment_mode_id": self.payment_method.id,
                "type": "S",
            }
        )

        # Set contract lines for the sponsorship
        contract_lines = sponsorship._get_sponsorship_standard_lines(False)
        if not self.sponsorship_plus:
            # Remove sponsorship+ from the contract
            contract_lines = contract_lines[:-1]

        sponsorship.contract_line_ids = contract_lines

        # Return the new sponsorship
        return sponsorship
