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
    def _signup_with_values(self, token, values):
        super()._signup_with_values(token, values)
        request.env.user.partner_id.legal_agreement_date = datetime.now()
