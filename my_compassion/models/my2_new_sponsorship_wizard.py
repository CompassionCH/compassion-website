from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# The single page of the fast checkout: e-mail, consent and one button per
# payment mode. It is all a public visitor answers before paying - the mode
# button they press both picks the mode and ends the flow. Everything else
# about them is collected afterwards.
FAST_CHECKOUT_STEP = "my_compassion.new_sponsorship_wizard_step_fast_checkout"

# The pre-payment identity steps the fast checkout stands in for. Substituted
# in _get_step_xmlids rather than edited out of every STEPS_CONFIGS entry, so
# a flow's entry keeps listing the steps it owns and Write&Pray gets the same
# slim step without the decision being spelled out twice.
DEFERRED_DETAIL_STEPS = (
    "my_compassion.new_sponsorship_wizard_step_user_details",
    "my_compassion.new_sponsorship_wizard_step_communication_details",
)


class NewSponsorshipWizard(models.TransientModel):
    _name = "new.sponsorship.wizard"
    _description = "New Sponsorship Wizard"

    STEPS_CONFIGS = {
        "standard": {
            # One page: the fast-checkout step carries the payment-mode
            # buttons itself, so there is no second step to select one on.
            "public": [
                FAST_CHECKOUT_STEP,
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
    details_deferred = fields.Boolean(
        compute="_compute_details_deferred",
        readonly=True,
        help="The flow went through the fast-checkout step, so the sponsor's"
        " identity is collected after payment instead of before it. The only"
        " signal the placeholder-name handling is allowed to key on: keying"
        " it on 'is this the public flow' would silently change every other"
        " flow sharing finish_sponsorship().",
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

    # Privacy/data consent of the fast-checkout step. Persisted on the partner
    # as legal_agreement_date, the same field the portal's own privacy
    # acceptance writes (see controllers/my_account.py).
    privacy_consent = fields.Boolean()

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

    @api.depends("sponsorship_type", "user_id")
    def _compute_details_deferred(self):
        for wizard in self:
            wizard.details_deferred = FAST_CHECKOUT_STEP in wizard._get_step_xmlids(
                wizard.sponsorship_type, wizard.user_id._is_public()
            )

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
        update_field("privacy_consent", "privacy_consent", bool)

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

        # A switch between flows (the Write&Pray age modal offers a standard
        # sponsorship instead) changes the step list under the index, and the
        # new flow is not necessarily as long as the one left behind. An index
        # past its end reads as "done" and would finish the wizard without
        # ever showing the step still to answer - the payment-mode buttons of
        # the one-page standard checkout, in exactly that case.
        if self.n_steps and self.current_step_idx >= self.n_steps:
            self.current_step_idx = self.n_steps - 1

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
        vals = {
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
        if self.details_deferred and not (self.firstname or self.lastname):
            # A nameless partner cannot exist: partner_firstname's _check_name
            # needs one of the two parts, and every PSP billing payload needs a
            # non-empty partner.name (payment_utils.split_partner_name raises on
            # an empty one). The real name lands later, from the payment
            # notification or from the post-payment details form.
            vals.update(
                {
                    "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                    "firstname": False,
                    "my2_name_placeholder": True,
                }
            )
        return vals

    def _get_offered_payment_modes(self):
        """The payment modes the checkout offers, for the website's company.

        One lookup behind both the buttons of the fast-checkout page and the
        dropdown of the logged-in step, so a mode can never be offered by one
        and unknown to the other. It is a display list, never a decision:
        whatever comes back is re-validated in _get_validated_payment_mode.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        return (
            self.env["account.payment.mode"]
            .sudo()
            .search(
                [
                    ("is_published", "=", True),
                    ("company_id", "=", company.id),
                ]
            )
        )

    def _get_payment_mode_buttons(self):
        """The payment modes the current step submits itself with, one button
        each: pressing one picks the mode and ends the flow in one action.

        Empty for every step that keeps the generic Continue/Finish button:
        the Write&Pray steps, since a Write&Pray sponsorship is deliberately
        created without a payment mode (see finish_sponsorship), and the
        logged-in payment step, which keeps its dropdown - the DOM contract
        the Switzerland eBill extension is built on.
        """
        self.ensure_one()
        if self.sponsorship_type == "write_and_pray":
            return self.env["account.payment.mode"]
        if self.current_step != self.env.ref(FAST_CHECKOUT_STEP):
            return self.env["account.payment.mode"]
        return self._get_offered_payment_modes()

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

        if self.details_deferred and not self.privacy_consent:
            # The consent tick is the only thing the fast-checkout step asks
            # besides the email. The step marks it required, but a checkbox is
            # trivially omitted from a posted form.
            raise ValidationError(
                _("Please accept the privacy notice before continuing.")
            )

        company = self.company_id or self.env.company
        partner = self.user_id.partner_id
        if self.user_id._is_public():
            # Look for existing partner, create one if not found
            partner_vals = self._get_new_partner_vals()
            if partner_vals.get("my2_name_placeholder"):
                # A placeholder can never match a returning sponsor's real
                # stored name, and feeding it to the fuzzy/ilike rules would
                # risk matching an unrelated partner instead, so matching is
                # skipped rather than run on a value that cannot inform it.
                partner = self.env["res.partner"].create(partner_vals)
            else:
                partner = self.env["res.partner.match"].match_values_to_partner(
                    partner_vals, match_update=False, match_create=False
                )
                if not partner:
                    partner = self.env["res.partner"].create(partner_vals)
        else:
            if not partner.birthdate_date and self.birthdate:
                partner.sudo().write({"birthdate_date": self.birthdate})

        if self.privacy_consent and not partner.legal_agreement_date:
            partner.sudo().write({"legal_agreement_date": fields.Datetime.now()})

        if not partner.country_id:
            country = self.country or company.country_id
            if not country:
                raise ValidationError(
                    _("Please add your country before sponsoring a child.")
                )
            partner.sudo().write({"country_id": country.id})

        # Create new sponsorship
        # Write&Pray sponsorships are never collected. They must stay without
        # a payment mode, otherwise the charge cron picks up their invoices.
        payment_mode = (
            self.env["account.payment.mode"]
            if self.sponsorship_type == "write_and_pray"
            else self._get_validated_payment_mode(company)
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            partner, company, payment_mode
        )
        sponsorship_values = {
            "partner_id": partner.id,
            "child_id": self.child_id.id,
            "group_id": group.id,
            "type": "SWP" if self.sponsorship_type == "write_and_pray" else "S",
            # Durable marker so only wizard signups ever get the portal
            # invitation email. Staff-created or imported contracts never do.
            "my2_signup": True,
        }
        # The contract is created in draft. Bank-collected sponsorships stay
        # draft until staff validate them by hand. Digital sponsorships are
        # activated by the payment flow once the first online payment succeeds.
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

    @api.model
    def _get_step_xmlids(self, sponsorship_type, is_public):
        """XML ids of the steps of one flow, in order.

        Public flows run the fast checkout: the identity steps are replaced by
        the single slim page, wherever a flow still lists them - which leaves
        the standard flow with that one page and nothing else. Logged-in flows
        are untouched: their sponsor is already identified.
        """
        xml_ids = self.STEPS_CONFIGS[sponsorship_type][
            "public" if is_public else "logged_in"
        ]
        if not is_public:
            return list(xml_ids)
        steps = []
        for xml_id in xml_ids:
            if xml_id in DEFERRED_DETAIL_STEPS:
                xml_id = FAST_CHECKOUT_STEP
            if xml_id not in steps:
                steps.append(xml_id)
        return steps

    @api.model
    def _flow_n_steps(self, sponsorship_type, is_public):
        """Step count of a flow, for the pages that continue the wizard's
        progress bar after the wizard record itself is gone (the payment and
        thank-you pages)."""
        return len(self._get_step_xmlids(sponsorship_type, is_public))

    def _get_steps(self):
        return [
            self.env.ref(xml_id).id
            for xml_id in self._get_step_xmlids(
                self.sponsorship_type, self.user_id._is_public()
            )
        ]


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
