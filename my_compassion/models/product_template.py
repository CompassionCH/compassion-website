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
    my_compassion_donation_quantity_low = fields.Integer(
        default=1, help="Lowest quantity suggestion when making a donation"
    )

    my_compassion_donation_quantity_medium = fields.Integer(
        default=3, help="Medium quantity suggestion when making a donation"
    )

    my_compassion_donation_quantity_high = fields.Integer(
        default=5, help="Highest quantity suggestion when making a donation"
    )
