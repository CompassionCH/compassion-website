from odoo import models


class RecurringContractOrigin(models.Model):
    # Makes it possible to publish origins in the sponsorship form
    _inherit = ["recurring.contract.origin", "website.published.mixin"]
    _name = "recurring.contract.origin"
