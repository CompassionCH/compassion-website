##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models

from odoo.addons.payment_payu_gpo import const


class Website(models.Model):
    _inherit = "website"

    def _my2_donation_cardholder_name_asked(self):
        """Whether the email step of a donation asks the name on the card,
        and how: False when no published PayU provider of the website's
        company is enabled, "required" when PayU is the only one (every
        payment then goes through it), "optional" otherwise (another
        provider may take no card)."""
        self.ensure_one()
        providers = (
            self.env["payment.provider"]
            .sudo()
            .search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("state", "in", ("enabled", "test")),
                    ("is_published", "=", True),
                ]
            )
        )
        payu = providers.filtered(lambda p: p.code == const.PROVIDER_CODE)
        if not payu:
            return False
        return "required" if payu == providers else "optional"
