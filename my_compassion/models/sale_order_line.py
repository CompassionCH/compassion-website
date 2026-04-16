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
        "recurring.contract", "Gift Recipient", ondelete="set null"
    )

    def _prepare_invoice_line(self, **optional_values):
        """Propagate gift recipient contract to the invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        if self.is_gift and self.gift_recipient_id:
            res["contract_id"] = self.gift_recipient_id.id
        return res
