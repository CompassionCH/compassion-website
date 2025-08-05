from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    activate_for_my_compassion = fields.Boolean(
        help="Publish the product as an available donation on the MyCompassion website"
    )

    # General
    my_compassion_name = fields.Char(
        required=True,
        translate=True,
        help="Name of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_pictogram = fields.Selection(
        [
            ("Advocacy", "Advocacy"),
            ("BibleGift", "Bible Gift"),
            ("BirthdayGift", "Birthday Gift"),
            ("BuildingsCity", "Buildings City"),
            ("BuildingsHouse", "Buildings House"),
            ("BuildingsNeighbourhood", "Buildings Neighbourhood"),
            ("BuildingsRural", "Buildings Rural"),
            ("CentreGift", "Centre Gift"),
            ("ChildFocused", "Child Focused"),
            ("ChildSponsorship", "Child Sponsorship"),
            ("Children", "Children"),
            ("ChristCentred", "Christ Centred"),
            ("ChristmasGift", "Christmas Gift"),
            ("ChurchBased", "Church Based"),
            ("CognitiveBrain", "Cognitive Brain"),
            ("CriticalNeeds", "Critical Needs"),
            ("DisasterRelief", "Disaster Relief"),
            ("EducationAndTraining", "Education And Training"),
            ("Family", "Family"),
            ("FamilyGift", "Family Gift"),
            ("Food", "Food"),
            ("GiftDonationGeneral", "Gift Donation General"),
            ("GlobeGlobal", "Globe Global"),
            ("Health", "Health"),
            ("HighlyVulnerableChildren", "Highly Vulnerable Children"),
            ("IncomeGeneration", "Income Generation"),
            ("Infrastructure", "Infrastructure"),
            ("LetterWriting", "Letter Writing"),
            ("LocalEmpowermentPartnership", "Local Empowerment Partnership"),
            ("LocationPin", "Location Pin"),
            ("MothersAndBabies", "Mothers And Babies"),
            ("Neighbourhood", "Neighbourhood"),
            ("Physical", "Physical"),
            ("SocioEmotional", "Socio Emotional"),
            ("Spiritual", "Spiritual"),
            ("UnsponsoredChildren", "Unsponsored Children"),
            ("Virus", "Virus"),
            ("WaterAndSanitation", "Water And Sanitation"),
            ("WereMostNeeded", "Were Most Needed"),
        ],
        string="Pictogram",
        required=True,
        help="Pictogram of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_description = fields.Text(
        required=True,
        translate=True,
        help="Description of the fund/gift visible on the MyCompassion website",
    )

    my_compassion_image = fields.Image(
        max_width=1200,
        max_height=900,
        required=True,
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


class DonationImpactLine(models.Model):
    """
    Represents a single line item in an impact statement, either
    describing the current situation or the impact of a donation.
    """

    _name = "donation.impact.line"
    _description = "Donation Impact Line"
    _order = "sequence, id"

    donation_id = fields.Many2one(
        "product.template",
        string="Donation Reference",
        required=True,
        ondelete="cascade",
    )

    # Enables drag and drop reordering
    sequence = fields.Integer(default=10)

    description = fields.Char(string="Statement", translate=True, required=True)

    type = fields.Selection(
        [("before", "Current Situation"), ("after", "Donation Impact")],
        string="Type",
        required=True,
        help="Used to distinguish between the two types.",
    )


class DonationInfoLine(models.Model):
    """
    Represents a single line item in an information statement.
    """

    _name = "donation.info.line"
    _description = "Donation Information Line"
    _order = "sequence, id"

    donation_id = fields.Many2one(
        "product.template",
        string="Donation Reference",
        required=True,
        ondelete="cascade",
    )

    # Enables drag and drop reordering
    sequence = fields.Integer(default=10)

    title = fields.Char(string="Title", translate=True, required=True)
    text = fields.Text(string="Text", translate=True, required=True)
