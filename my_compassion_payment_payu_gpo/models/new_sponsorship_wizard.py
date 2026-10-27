##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_payu_gpo import const


class NewSponsorshipWizard(models.TransientModel):
    _inherit = "new.sponsorship.wizard"

    cardholder_name = fields.Char(
        help="Name on the card, asked under the e-mail of the fast checkout"
        " when the website offers PayU: the card form of the payment page"
        " then takes it instead of asking it again."
    )

    def _my2_asks_cardholder_name(self):
        """The standard fast checkout of a company that offers PayU asks the
        name on the card, the only thing PayU's card form needs besides the
        card. Other companies keep their page unchanged."""
        self.ensure_one()
        return bool(
            self.details_deferred
            and self.sponsorship_type != "write_and_pray"
            and self._get_offered_payment_modes().filtered(
                lambda mode: mode.payment_provider_id.code == const.PROVIDER_CODE
            )
        )

    def update(self, post):
        if "cardholder_name" in post:
            # Same normalization as the name typed on PayU's card form.
            self.cardholder_name = " ".join(str(post["cardholder_name"] or "").split())[
                :100
            ]
        return super().update(post)

    def finish_sponsorship(self):
        self.ensure_one()
        if self._my2_asks_cardholder_name() and not self.cardholder_name:
            # The page marks the field required, but a posted form can omit it.
            raise ValidationError(_("Please enter the name on the card."))
        return super().finish_sponsorship()
