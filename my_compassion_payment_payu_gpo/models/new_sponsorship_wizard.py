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

from ..utils import normalize_cardholder_name


class NewSponsorshipWizard(models.TransientModel):
    _inherit = "new.sponsorship.wizard"

    cardholder_firstname = fields.Char(
        help="First name on the card, asked under the e-mail of the fast"
        " checkout when the website offers PayU: the card form of the payment"
        " page then comes prefilled with it."
    )
    cardholder_lastname = fields.Char(
        help="Last name on the card, asked with the first name."
    )
    payu_gpo_sponsorship_id = fields.Many2one(
        "recurring.contract",
        help="The sponsorship the wizard finished, to key the names on the"
        " card by on their way to the payment page.",
    )

    def _my2_is_payu_gpo_mode(self, mode):
        return (
            mode.payment_provider_id.code == const.PROVIDER_CODE
            and mode.payment_provider_id.state != "disabled"
        )

    def _my2_asks_cardholder_name(self):
        """The standard fast checkout of a company that offers PayU asks the
        first and last name on the card, the only thing PayU's card form
        needs besides the card. Other companies keep their page unchanged."""
        self.ensure_one()
        return bool(
            self.details_deferred
            and self.sponsorship_type != "write_and_pray"
            and self._get_offered_payment_modes().filtered(self._my2_is_payu_gpo_mode)
        )

    def update(self, post):
        for field in ("cardholder_firstname", "cardholder_lastname"):
            if field in post:
                self[field] = normalize_cardholder_name(post[field])
        return super().update(post)

    def finish_sponsorship(self):
        """The names are required only to pay with PayU: the other modes on
        the page (e.g. a standing order) take no card."""
        self.ensure_one()
        if (
            self._my2_asks_cardholder_name()
            and self._my2_is_payu_gpo_mode(self.payment_method)
            and not (self.cardholder_firstname and self.cardholder_lastname)
        ):
            # The page requires them for the PayU button, but a posted form
            # can omit them.
            raise ValidationError(
                _("Please enter the first and last name on the card.")
            )
        sponsorship = super().finish_sponsorship()
        self.payu_gpo_sponsorship_id = sponsorship
        return sponsorship
