from odoo import fields, models


class DonationImpactLine(models.Model):
    """
    Represents a single line in the impact statement of a donation web page, either
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
