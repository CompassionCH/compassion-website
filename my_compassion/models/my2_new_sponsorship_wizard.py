from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class NewSponsorshipWizard(models.TransientModel):
    _name = "new.sponsorship.wizard"
    _description = "New Sponsorship Wizard"

    STEPS_CONFIGS = {
        "standard": {
            "public": [
                "my_compassion.new_sponsorship_wizard_step_user_details",
                "my_compassion.new_sponsorship_wizard_step_communication_details",
                "my_compassion.new_sponsorship_wizard_step_payment_methods",
            ],
            "logged_in": [
                "my_compassion.new_sponsorship_wizard_step_payment_methods",
            ],
        },
        "write_and_pray": {
            "public": [
                "my_compassion.new_sponsorship_wizard_step_user_details",
                "my_compassion.new_sponsorship_wizard_step_communication_details",
                "my_compassion.new_sponsorship_wizard_step_wap_options",
            ],
            "logged_in": [
                "my_compassion.new_sponsorship_wizard_step_wap_options",
            ],
        },
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
    company_id = fields.Many2one(
        "res.company",
        help="Company of the website the wizard was started on; scopes the "
        "offered payment modes and the contract group.",
    )
    child_id = fields.Many2one(
        "compassion.child",
        required=True,
    )
    sponsorship_type = fields.Selection(
        [
            ("standard", "Standard"),
            ("write_and_pray", "Write&Pray"),
        ],
        string="Sponsorship type",
        default="standard",
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

    # Write&Pray fields
    wap_contribution_amount = fields.Float()

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

    @api.depends("current_step_idx", "sponsorship_type", "user_id")
    def _compute_current_step(self):
        for wizard in self:
            steps = wizard._get_steps()
            if 0 <= wizard.current_step_idx < len(steps):
                wizard.current_step = steps[wizard.current_step_idx]
            else:
                wizard.current_step = False

    @api.depends("sponsorship_type", "user_id")
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

        update_field("sponsorship_type", "sponsorship_type")

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
        update_field("country", "country", int)

        update_field("payment_method", "payment_method", int)
        update_field("sponsorship_plus", "sponsorship_plus", bool)

        if post.get("contribute") == "true":
            if post.get("suggested_amount") == "custom":
                update_field("wap_contribution_amount", "custom_amount", float)
            else:
                update_field("wap_contribution_amount", "suggested_amount", float)
        elif post.get("contribute") == "false":
            values["wap_contribution_amount"] = 0

        spoken_languages_ids = [
            int(post.get(key)) for key in post if key.startswith("spoken_language")
        ]
        if spoken_languages_ids:
            values["spoken_languages"] = [(6, 0, spoken_languages_ids)]
        update_field("lead_source", "lead_source", int)

        initial_step = self.current_step

        self.write(values)

        # Move to previous / next step (only if current step didn't change)
        action = post.get("action")
        if action == "next" and initial_step.id == self.current_step.id:
            self.current_step_idx = min(self.current_step_idx + 1, self.n_steps)
        elif action == "previous":
            self.current_step_idx = max(self.current_step_idx - 1, 0)

    def _get_new_partner_vals(self):
        """Values used to match or create the partner of a public signup.
        Country extensions add their own keys before the matching runs.
        """
        self.ensure_one()
        return {
            "title": self.title.id,
            "lastname": self.lastname,
            "firstname": self.firstname,
            "birthdate_date": self.birthdate,
            "email": self.email,
            "phone": self.phone,
            "street": f"{self.street or ''} {self.street_number or ''}".strip(),
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country.id,
            "spoken_lang_ids": [(4, lang.id) for lang in self.spoken_languages],
        }

    def _get_validated_payment_mode(self, company):
        """Return the selected payment mode, validated against the website company.

        The step form posts a raw id, so the choice is re-validated server-side.
        It must be active, published and belong to the website's company.
        Empty when no mode was selected (e.g. a flow without a payment step).
        """
        self.ensure_one()
        if not self.payment_method:
            return self.env["account.payment.mode"]
        mode = self.payment_method
        if not mode.active or not mode.is_published or mode.company_id != company:
            raise ValidationError(_("The selected payment method is not available."))
        return mode

    def finish_sponsorship(self):
        self.ensure_one()

        partner = self.user_id.partner_id
        if self.user_id._is_public():
            # Look for existing partner, create one if not found
            partner_vals = self._get_new_partner_vals()
            partner = self.env["res.partner.match"].match_values_to_partner(
                partner_vals, match_update=False, match_create=False
            )
            if not partner:
                partner = self.env["res.partner"].create(partner_vals)
        else:
            if not partner.birthdate_date and self.birthdate:
                partner.sudo().write({"birthdate_date": self.birthdate})

        # Create new sponsorship
        company = self.company_id or self.env.company
        payment_mode = self._get_validated_payment_mode(company)
        group = self.env["recurring.contract.group"]._find_or_create_group(
            partner, company, payment_mode
        )
        sponsorship_values = {
            "partner_id": partner.id,
            "child_id": self.child_id.id,
            "group_id": group.id,
            "type": "SWP" if self.sponsorship_type == "write_and_pray" else "S",
        }
        # The contract is created in draft; bank-collected sponsorships are
        # validated manually by staff before they start billing. TODO
        # this has to change when recurring digital billing works.
        sponsorship = self.env["recurring.contract"].create(sponsorship_values)

        # Set contract lines for the sponsorship
        contract_lines = sponsorship._get_sponsorship_standard_lines(
            self.sponsorship_type == "write_and_pray"
        )
        if not self.sponsorship_plus:
            # Remove sponsorship+ from the contract
            contract_lines = contract_lines[:-1]
        # Add Write&Pray contribution
        if (
            self.sponsorship_type == "write_and_pray"
            and self.wap_contribution_amount > 0
        ):
            contract_lines[-1][2].update(
                {
                    "quantity": 1,
                    "amount": self.wap_contribution_amount,
                    "subtotal": self.wap_contribution_amount,
                }
            )
        sponsorship.contract_line_ids = contract_lines

        # Return the new sponsorship
        return sponsorship

    def _get_steps(self):
        xml_ids = self.STEPS_CONFIGS[self.sponsorship_type][
            "public" if self.user_id._is_public() else "logged_in"
        ]
        return [self.env.ref(xml_id).id for xml_id in xml_ids]


class NewSponsorshipWizardStep(models.Model):
    _name = "new.sponsorship.wizard.step"
    _description = "New Sponsorship Wizard Step"

    title = fields.Char(translate=True)

    template = fields.Many2one(
        "ir.ui.view",
        string="Qweb Template",
        required=True,
        domain=[
            ("type", "=", "qweb"),
        ],
    )
