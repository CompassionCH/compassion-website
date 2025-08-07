from odoo import fields, models


class DonationInfoLine(models.Model):
    """
    Represents a single item in the information section of a donation web page.
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
