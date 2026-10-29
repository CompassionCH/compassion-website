from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Per company: each office publishes its own funds and gifts (the products
    # are shared between the companies).
    activate_for_my_compassion = fields.Boolean(
        company_dependent=True,
        help="Publish the product as an available donation on the MyCompassion "
        "website of the current company",
    )

    # General
    my_compassion_donation_type = fields.Selection(
        [
            ("fund", "Fund"),
            ("gift", "Gift"),
        ],
        string="Donation Type",
    )

    my_compassion_name = fields.Char(
        translate=True,
        help="Name of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_color = fields.Many2one(
        "theme.compassion.colors",
        string="Color",
        help="Thematic color of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_pictogram = fields.Many2one(
        "theme.compassion.pictograms",
        string="Pictogram",
        help="The pictogram for the fund/gift visible on the MyCompassion website.",
    )

    my_compassion_description = fields.Text(
        translate=True,
        help="Description of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_image = fields.Image(
        max_width=1200,
        max_height=900,
        help="Image of the fund/gift visible on the MyCompassion website",
    )

    # Impact statement
    my_compassion_show_impact_statement = fields.Boolean(
        default=False,
        help="Display the impact statement on the web page of the fund/gift",
    )

    my_compassion_impact_before_ids = fields.One2many(
        "donation.impact.line",
        "donation_id",
        string="Current Situation",
        domain=[("type", "=", "before")],
        context={"default_type": "before"},
        help="Lines for the current reality displayed on the web page of the fund/gift",
    )

    my_compassion_impact_after_ids = fields.One2many(
        "donation.impact.line",
        "donation_id",
        string="Donation Impact",
        domain=[("type", "=", "after")],
        context={"default_type": "after"},
        help="Lines for the donation impact displayed on the web page of the fund/gift",
    )

    # Information lines
    my_compassion_show_info = fields.Boolean(
        default=False,
        help="Display the information lines on the web page of the fund/gift",
    )

    my_compassion_info_ids = fields.One2many(
        "donation.info.line",
        "donation_id",
        string="Information",
        help="Information lines displayed on the web page of the fund/gift",
    )

    # Testimony
    my_compassion_show_testimony = fields.Boolean(
        default=False,
        help="Display the testimony section on the web page of the fund/gift",
    )

    my_compassion_testimony_title = fields.Char(
        string="Testimony Title",
        translate=True,
        help="Title of the testimony visible on the web page of the fund/gift",
    )

    my_compassion_testimony_text = fields.Text(
        string="Testimony Text",
        translate=True,
        help="Content of the testimony visible on the web page of the fund/gift",
    )

    # Donation suggestions, per company in the currency of the company: a
    # shared product's currency_id is always the main company's one. A company
    # that sets none reads the company-less ir.default values
    # (data/donation_amount_defaults.xml).
    my_compassion_donation_amount_low = fields.Float(
        string="Lowest Amount",
        company_dependent=True,
        copy=True,
        help="Lowest price suggestion when making a donation",
    )

    my_compassion_donation_amount_medium = fields.Float(
        string="Medium Amount",
        company_dependent=True,
        copy=True,
        help="Medium price suggestion when making a donation",
    )

    my_compassion_donation_amount_high = fields.Float(
        string="Highest Amount",
        company_dependent=True,
        copy=True,
        help="Highest price suggestion when making a donation",
    )

    my_compassion_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_my_compassion_currency_id",
        help="Currency of the suggested amounts: the current company's one",
    )

    @api.depends_context("company")
    def _compute_my_compassion_currency_id(self):
        self.my_compassion_currency_id = self.env.company.currency_id

    def get_donation_limits(self, company, partner, sponsorship_id=None, order=None):
        """
        Returns the donation limits for the product (optionally tied to a sponsorship)
        in the form:
        {
            "min_amount": int,               # If amount is limited
            "max_amount": int,               # If amount is limited
            "remaining_donations": int,      # If frequency is limited
        }
        `order` is the donor's current cart. Only that cart may be counted: an
        abandoned order stays in `draft` forever after a failed payment, so
        counting every open order lets a failed payment eat the allowance (T3451).
        """
        limits = {}
        product_limits = (
            self.env["gift.threshold.settings"]
            .sudo()
            .search([("gift_type_id", "=", self.sponsorship_gift_type_id.id)], limit=1)
        )
        if product_limits:
            limits["min_amount"] = product_limits.currency_id._convert(
                product_limits.min_amount,
                company.currency_id,
                company,
                fields.Date.today(),
            )
            limits["max_amount"] = product_limits.currency_id._convert(
                product_limits.max_amount,
                company.currency_id,
                company,
                fields.Date.today(),
            )

            if product_limits.gift_frequency:
                domain = [
                    ("partner_id", "=", partner.id),
                    ("gift_type_id", "=", self.sponsorship_gift_type_id.id),
                ]

                if sponsorship_id:
                    domain += [("sponsorship_id", "=", sponsorship_id)]

                if product_limits.yearly_threshold:
                    first_january_of_this_year = fields.Date.today().replace(
                        day=1, month=1
                    )
                    next_year = first_january_of_this_year.replace(
                        year=first_january_of_this_year.year + 1
                    )
                    domain += [
                        ("gift_date", ">=", first_january_of_this_year),
                        ("gift_date", "<", next_year),
                    ]

                other_gifts_count = (
                    self.env["sponsorship.gift"].sudo().search_count(domain)
                )
                # Add gifts currently in the donor's cart
                cart = order or self.env["sale.order"]
                order_lines = cart.sudo().order_line.filtered(
                    lambda line: line.product_template_id.id == self.id
                    and (
                        (not sponsorship_id)
                        or line.gift_recipient_id.id == sponsorship_id
                    )
                )
                other_gifts_count += len(order_lines)
                limits["remaining_donations"] = (
                    product_limits.gift_frequency - other_gifts_count
                )

        return limits
