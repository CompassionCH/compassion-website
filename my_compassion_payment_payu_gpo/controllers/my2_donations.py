##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import http
from odoo.http import request

from odoo.addons.my_compassion.controllers.my2_donations import (
    MyCompassionDonationsController,
)
from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    OWN_SIGNUPS_SESSION_LIMIT,
)

from ..utils import normalize_cardholder_name, session_cardholder_names

# The first and last names on the card typed on the email step of a
# donation, by order id, until the order is paid.
DONATION_CARDHOLDER_NAMES_SESSION_KEY = "my2_payu_gpo_donation_cardholder_names"


def _session_donation_cardholder_names():
    return session_cardholder_names(DONATION_CARDHOLDER_NAMES_SESSION_KEY)


class DonationsController(MyCompassionDonationsController):
    @http.route()
    def my2_gift_package_donor(self, email=None, privacy_consent=None, **post):
        """The email step also asks the first and last name on the card when
        the website offers PayU, kept for the card form of the payment that
        follows."""
        asked = request.website._my2_donation_cardholder_name_asked()
        typed = [
            normalize_cardholder_name(post.get(field))
            for field in ("cardholder_firstname", "cardholder_lastname")
        ]
        if (
            asked == "required"
            and not all(typed)
            and request.env.user._is_public()
            and email
            and privacy_consent
        ):
            return request.redirect("/my2/gift-package?donor_error=cardholder")
        response = super().my2_gift_package_donor(
            email=email, privacy_consent=privacy_consent, **post
        )
        order = request.website.sale_get_order()
        done = "donor_error" not in (response.location or "")
        if asked and done and order and self._get_session_donor(order.sudo()):
            names = _session_donation_cardholder_names()
            names.pop(str(order.id), None)
            if any(typed):
                names[str(order.id)] = typed
            # Kept as few as the session's own signups.
            request.session[DONATION_CARDHOLDER_NAMES_SESSION_KEY] = dict(
                list(names.items())[-OWN_SIGNUPS_SESSION_LIMIT:]
            )
        return response

    def _get_donor_step_values(self, order, **kwargs):
        """The names on the card of the email step, and the same names to
        prefill the card form of the payment, where they can still be
        corrected."""
        values = super()._get_donor_step_values(order, **kwargs)
        if values:
            firstname, lastname = _session_donation_cardholder_names().get(
                str(order.id), ["", ""]
            )
            values.update(
                {
                    "donor_cardholder_name_asked": (
                        request.website._my2_donation_cardholder_name_asked()
                    ),
                    "donor_cardholder_firstname": firstname,
                    "donor_cardholder_lastname": lastname,
                    "payu_gpo_cardholder_firstname": firstname,
                    "payu_gpo_cardholder_lastname": lastname,
                }
            )
        return values

    def _get_donor_details_values(self, sale_order, **kwargs):
        """The thank-you page shows once the order is paid: the names are no
        longer needed."""
        names = _session_donation_cardholder_names()
        if names.pop(str(sale_order.id), None):
            request.session[DONATION_CARDHOLDER_NAMES_SESSION_KEY] = names
        return super()._get_donor_details_values(sale_order, **kwargs)
