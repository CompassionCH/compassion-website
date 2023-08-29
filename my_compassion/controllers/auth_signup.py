##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime

from odoo import _
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.auth_signup.controllers.main import AuthSignupHome


class RegistrationController(AuthSignupHome):
    def do_signup(self, qcontext):
        """
        Check if a sponsor ref was given in order to try to match
        an existing sponsor.
        """
        sponsor_ref = qcontext.get("sponsor_ref")
        if sponsor_ref:
            sponsor = (
                request.env["res.partner"]
                .sudo()
                .search([("ref", "=", sponsor_ref)], limit=1)
            )
            if not sponsor:
                # Try to find based on a child reference, either global or local
                child = (
                    request.env["compassion.child"]
                    .sudo()
                    .search(
                        [
                            ("state", "=", "P"),
                            "|",
                            ("global_id", "=", sponsor_ref),
                            ("local_id", "=", sponsor_ref),
                        ],
                        limit=1,
                    )
                )
                sponsor = child.sponsor_id
            if sponsor:
                if sponsor.email.lower() != qcontext["login"].lower():
                    raise UserError(
                        _(
                            "The email address you entered is not the same "
                            "as the one in the system. Please try again."
                        )
                    )
                # Prepare token for signup
                sponsor.signup_prepare()
                qcontext["token"] = sponsor.signup_token
            else:
                raise UserError(
                    _("No sponsor found with this reference. Please try again.")
                )
        return super().do_signup(qcontext)

    def _signup_with_values(self, token, values):
        super()._signup_with_values(token, values)
        request.env.user.partner_id.legal_agreement_date = datetime.now()
