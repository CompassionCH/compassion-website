from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    activate_for_my_compassion = fields.Boolean(
        help="Publish the product as an available donation on the MyCompassion website"
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

    # Donation suggestions
    my_compassion_donation_amount_low = fields.Monetary(
        string="Lowest Amount",
        currency_field="currency_id",
        default=15.0,
        help="Lowest price suggestion when making a donation",
    )

    my_compassion_donation_amount_medium = fields.Monetary(
        string="Medium Amount",
        currency_field="currency_id",
        default=50.0,
        help="Medium price suggestion when making a donation",
    )

    my_compassion_donation_amount_high = fields.Monetary(
        string="Highest Amount",
        currency_field="currency_id",
        default=100.0,
        help="Highest price suggestion when making a donation",
    )

    def get_donation_limits(self, company, partner, sponsorship_id=None):
        """
        Returns the donation limits for the product (optionally tied to a sponsorship)
        in the form:
        {
            "min_amount": int,               # If amount is limited
            "max_amount": int,               # If amount is limited
            "remaining_donations": int,      # If frequency is limited
        }
        """
        limits = {}
        product_limits = (
            self.env["gift.threshold.settings"]
            .sudo()
            .search([("product_id", "=", self.id)], limit=1)
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
                gift_types = self.env["sponsorship.gift"].get_gift_types(self)

                domain = [
                    ("partner_id", "=", partner.id),
                    ("gift_type", "=", gift_types["gift_type"]),
                    ("attribution", "=", gift_types["attribution"]),
                    (
                        "sponsorship_gift_type",
                        "=",
                        gift_types.get("sponsorship_gift_type", False),
                    ),
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
                # Add gifts currently in the user's cart
                sale_order = (
                    self.env["sale.order"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", partner.id),
                            ("state", "in", ["draft", "sent"]),
                        ]
                    )
                )
                order_lines = sale_order.order_line.filtered(
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
