##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    OWN_SIGNUPS_SESSION_LIMIT,
    MyCompassionNewSponsorshipController,
    MyCompassionSponsorshipPayment,
)
from odoo.addons.my_compassion.controllers.website_utils import safe_int

from ..utils import session_cardholder_names

# The first and last names on the card typed on the fast checkout, by
# sponsorship id, until the first payment of that sponsorship: the wizard is
# gone by then.
CARDHOLDER_NAMES_SESSION_KEY = "my2_payu_gpo_cardholder_names"


def _session_cardholder_names():
    return session_cardholder_names(CARDHOLDER_NAMES_SESSION_KEY)


class NewSponsorshipController(MyCompassionNewSponsorshipController):
    @http.route()
    def sponsorship_wizard_submit(self, **post):
        response = super().sponsorship_wizard_submit(**post)
        wizard = (
            request.env["new.sponsorship.wizard"]
            .sudo()
            .browse(safe_int(post.get("wizard_id")))
            .exists()
        )
        typed = [wizard.cardholder_firstname or "", wizard.cardholder_lastname or ""]
        if any(typed) and wizard.payu_gpo_sponsorship_id:
            names = _session_cardholder_names()
            names[str(wizard.payu_gpo_sponsorship_id.id)] = typed
            # Kept as few as the session's own signups.
            request.session[CARDHOLDER_NAMES_SESSION_KEY] = dict(
                list(names.items())[-OWN_SIGNUPS_SESSION_LIMIT:]
            )
        return response

    @classmethod
    def _thank_you_values(cls, sponsorship, *args, **kwargs):
        """The thank-you page shows once the first payment is done (a refused
        one goes back to the payment page): the names are no longer needed."""
        names = _session_cardholder_names()
        if names.pop(str(sponsorship.id), None):
            request.session[CARDHOLDER_NAMES_SESSION_KEY] = names
        return super()._thank_you_values(sponsorship, *args, **kwargs)


class SponsorshipPayment(MyCompassionSponsorshipPayment):
    @classmethod
    def _get_sponsorship_payment_values(
        cls, sponsorship, provider, access_token, invoice
    ):
        """The card form of PayU comes prefilled with the first and last name
        typed on the fast checkout for this sponsorship, else with the
        sponsor's own, and can still be corrected, e.g. for another card
        after a refusal."""
        values = super()._get_sponsorship_payment_values(
            sponsorship, provider, access_token, invoice
        )
        names = _session_cardholder_names().get(str(sponsorship.id))
        partner = sponsorship.partner_id.sudo()
        if not names and not partner.my2_name_placeholder:
            names = [partner.firstname or "", partner.lastname or ""]
        if names:
            values.update(
                {
                    "payu_gpo_cardholder_firstname": names[0],
                    "payu_gpo_cardholder_lastname": names[1],
                }
            )
        return values
