from odoo import fields, models


class SalesOrderLine(models.Model):
    _inherit = "sale.order.line"

    frequency = fields.Selection(
        [
            ("one_time", "One-time"),
            ("monthly", "Monthly"),
        ],
        string="Frequency",
        default="one_time",
        required=True,
        help="Specify if the contract is for a single instance or recurs monthly.",
    )

    is_gift = fields.Boolean("Is a Gift")

    gift_recipient_id = fields.Many2one(
        "recurring.contract", "Gift Recipient", ondelete="cascade"
    )
