# Copyright 2023 Emanuel Cino <ecino@compassion.ch>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.addons.auth_signup.controllers.main import SIGN_UP_REQUEST_PARAMS


def post_load():
    """
    ADD sponsor_ref in the signup context
    """
    SIGN_UP_REQUEST_PARAMS.update({"sponsor_ref"})
