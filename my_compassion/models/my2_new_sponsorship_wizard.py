from odoo import api, fields, models


class NewSponsorshipWizard(models.TransientModel):
    _name = "new.sponsorship.wizard"
    _description = "New Sponsorship Wizard"

    STEP_CONFIGS = {
        "standard": {
            "public": [
                "my_compassion.new_sponsorship_wizard_step_user_details",
                "my_compassion.new_sponsorship_wizard_step_payment_methods",
            ],
            "logged_in": [
                "my_compassion.new_sponsorship_wizard_step_payment_methods",
            ],
        }
    }

    current_step_idx = fields.Integer()
    current_step = fields.Many2one(
        "new.sponsorship.wizard.step",
        compute="_compute_current_step",
        readonly=True,
    )
    n_steps = fields.Integer(
        compute="_compute_n_steps",
        readonly=True,
    )
    is_done = fields.Boolean(
        compute="_compute_is_done",
        readonly=True,
    )

    user_id = fields.Many2one(
        "res.users",
        required=True,
    )
    child_id = fields.Many2one(
        "compassion.child",
        required=True,
    )

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

    @api.depends("current_step_idx", "user_id")
    def _compute_current_step(self):
        for wizard in self:
            steps = wizard._get_steps()
            if 0 <= wizard.current_step_idx < len(steps):
                wizard.current_step = steps[wizard.current_step_idx]
            else:
                wizard.current_step = False

    @api.depends("user_id")
    def _compute_n_steps(self):
        for wizard in self:
            wizard.n_steps = len(wizard._get_steps())

    @api.depends("current_step_idx", "n_steps")
    def _compute_is_done(self):
        for wizard in self:
            wizard.is_done = wizard.current_step_idx >= wizard.n_steps

    def update(self, post):
        values = {}

        def update_field(field, key, convert=lambda x: x):
            try:
                values[field] = convert(post[key])
            except (ValueError, TypeError, KeyError):
                pass

        update_field("title", "title", int)
        update_field("lastname", "lastname")
        update_field("firstname", "firstname")
        update_field("birthdate", "birthdate")
        update_field("email", "email")
        update_field("phone", "phone")
        update_field("street", "street")
        update_field("street_number", "street_number")
        update_field("zip", "zip")
        update_field("city", "city")
        update_field("country", "country")

        update_field("payment_method", "payment_method", int)
        update_field("sponsorship_plus", "sponsorship_plus", bool)

        spoken_languages_ids = [
            int(post.get(key)) for key in post if key.startswith("spoken_language")
        ]
        if spoken_languages_ids:
            values["spoken_languages"] = [(6, 0, spoken_languages_ids)]
        update_field("lead_source", "lead_source", int)
        update_field("volunteering", "volunteering", bool)

        self.write(values)

        # Move to previous / next step
        action = post.get("action")
        if action == "next":
            if self.current_step_idx <= self.n_steps:
                self.current_step_idx += 1
        elif action == "previous":
            if self.current_step_idx > 0:
                self.current_step_idx -= 1

    def finish_sponsorship(self):
        self.ensure_one()

        partner = self.user_id.partner_id
        if self.user_id._is_public():
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
                "child_id": self.child_id.id,
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

    def _get_steps(self):
        xml_ids = self.STEP_CONFIGS["standard"][
            "public" if self.user_id._is_public() else "logged_in"
        ]
        return [self.env.ref(xml_id).id for xml_id in xml_ids]


class NewSponsorshipWizardStep(models.Model):
    _name = "new.sponsorship.wizard.step"
    _description = "New Sponsorship Wizard Step"

    title = fields.Char()

    template = fields.Many2one(
        "ir.ui.view",
        string="Qweb Template",
        required=True,
        domain=[
            ("type", "=", "qweb"),
        ],
    )
