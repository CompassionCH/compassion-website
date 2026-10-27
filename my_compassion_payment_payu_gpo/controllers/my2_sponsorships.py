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
    MyCompassionNewSponsorshipController,
    MyCompassionSponsorshipPayment,
)
from odoo.addons.my_compassion.controllers.website_utils import safe_int

# The name on the card typed on the fast checkout, until the payment page of
# the sponsorship it started: the wizard is gone by then.
CARDHOLDER_NAME_SESSION_KEY = "my2_payu_gpo_cardholder_name"


class NewSponsorshipController(MyCompassionNewSponsorshipController):
    @http.route()
    def sponsorship_wizard_submit(self, **post):
        wizard = (
            request.env["new.sponsorship.wizard"]
            .sudo()
            .browse(safe_int(post.get("wizard_id")))
            .exists()
        )
        cardholder_name = wizard.cardholder_name if wizard else False
        response = super().sponsorship_wizard_submit(**post)
        if cardholder_name:
            request.session[CARDHOLDER_NAME_SESSION_KEY] = cardholder_name
        return response


class SponsorshipPayment(MyCompassionSponsorshipPayment):
    @classmethod
    def _get_sponsorship_payment_values(
        cls, sponsorship, provider, access_token, invoice
    ):
        """The card form of PayU takes the name typed on the fast checkout
        (see payment_templates.xml). Only for a sponsor still known by email
        only: anyone else never typed one there."""
        values = super()._get_sponsorship_payment_values(
            sponsorship, provider, access_token, invoice
        )
        if sponsorship.partner_id.sudo().my2_name_placeholder:
            values["payu_gpo_cardholder_name"] = request.session.get(
                CARDHOLDER_NAME_SESSION_KEY
            )
        return values
