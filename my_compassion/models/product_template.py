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

    my_compassion_color = fields.Selection(
        [
            ('core-blue', 'Core Blue'),
            ('dark-blue', 'Dark Blue'),
            ('low-blue', 'Low Blue'),
            ('mid-blue', 'Mid Blue'),
            ('high-blue', 'High Blue'),
            ('low-green', 'Low Green'),
            ('mid-green', 'Mid Green'),
            ('high-green', 'High Green'),
            ('low-yellow', 'Low Yellow'),
            ('mid-yellow', 'Mid Yellow'),
            ('high-yellow', 'High Yellow'),
            ('low-pink', 'Low Pink'),
            ('mid-pink', 'Mid Pink'),
            ('high-pink', 'High Pink'),
            ('low-orange', 'Low Orange'),
            ('mid-orange', 'Mid Orange'),
            ('high-orange', 'High Orange'),
            ('low-brown', 'Low Brown'),
            ('mid-brown', 'Mid Brown'),
            ('high-brown', 'High Brown'),
            ('low-black', 'Low Black'),
            ('off-black', 'Off Black'),
            ('low-grey', 'Low Grey'),
            ('mid-grey', 'Mid Grey'),
            ('low-eggshell', 'Low Eggshell'),
            ('mid-eggshell', 'Mid Eggshell'),
            ('high-eggshell', 'High Eggshell'),
            ('pure-white', 'Pure White'),
        ],
        string="Color",
        help="Thematic color of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_pictogram = fields.Selection(
        [
            ("advocacy", "Advocacy"),
            ("bible-gift", "Bible Gift"),
            ("birthday-gift", "Birthday Gift"),
            ("buildings-city", "Buildings City"),
            ("buildings-house", "Buildings House"),
            ("buildings-neighbourhood", "Buildings Neighbourhood"),
            ("buildings-rural", "Buildings Rural"),
            ("centre-gift", "Centre Gift"),
            ("child-focused", "Child Focused"),
            ("child-sponsorship", "Child Sponsorship"),
            ("children", "Children"),
            ("christ-centred", "Christ Centred"),
            ("christmas-gift", "Christmas Gift"),
            ("church-based", "Church Based"),
            ("cognitive-brain", "Cognitive Brain"),
            ("critical-needs", "Critical Needs"),
            ("disaster-relief", "Disaster Relief"),
            ("education-and-training", "Education And Training"),
            ("family", "Family"),
            ("family-gift", "Family Gift"),
            ("food", "Food"),
            ("gift-donation-general", "Gift Donation General"),
            ("globe-global", "Globe Global"),
            ("health", "Health"),
            ("highly-vulnerable-children", "Highly Vulnerable Children"),
            ("income-generation", "Income Generation"),
            ("infrastructure", "Infrastructure"),
            ("letter-writing", "Letter Writing"),
            ("local-empowerment-partnership", "Local Empowerment Partnership"),
            ("location-pin", "Location Pin"),
            ("mothers-and-babies", "Mothers And Babies"),
            ("neighbourhood", "Neighbourhood"),
            ("physical", "Physical"),
            ("socio-emotional", "Socio Emotional"),
            ("spiritual", "Spiritual"),
            ("unsponsored-children", "Unsponsored Children"),
            ("virus", "Virus"),
            ("water-and-sanitation", "Water And Sanitation"),
            ("were-most-needed", "Were Most Needed"),
        ],
        string="Pictogram",
        help="Pictogram of the fund/gift visible on the MyCompassion website",
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
