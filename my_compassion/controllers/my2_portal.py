##############################################################################
#
#    Copyright (C) 2025 Compassion CH (https://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################


from odoo import _
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyCompassionPortal(CustomerPortal):
    """
    Inherits from Odoo's base CustomerPortal to provide specific overrides for the
    My Compassion 2.0 website. This is the central place to customize core portal
    behavior while keeping the logic isolated to the My Compassion 2.0 theme.

    Also, most of the code here is ported from My Compassion 1.0 my_account.py.
    """

    def _update_password(self, old, new1, new2):
        """
        TODO: Delete me in Odoo 16.0
        Fixes a bug present in Odoo < 16.0
        Related fix commit in Odoo repository:
        https://github.com/odoo/odoo/commit/6fea44277edef8ae7058e7bae9c69e84a026cfb8
        """
        for k, v in [("old", old), ("new1", new1), ("new2", new2)]:
            if not v:
                return {
                    "errors": {
                        "password": {k: _("You cannot leave any password empty.")}
                    }
                }
        if new1 != new2:
            return {
                "errors": {
                    "password": {
                        "new2": _(
                            "The new password and its confirmation must be identical."
                        )
                    }
                }
            }

        try:
            request.env["res.users"].change_password(old, new1)
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _(
                    "The old password you provided is incorrect, your password was not "
                    "changed."
                )
            return {"errors": {"password": {"old": msg}}}
        except UserError as e:
            return {"errors": {"password": e.name}}

        new_token = request.env.user._compute_session_token(request.session.sid)
        request.session.session_token = new_token

        return {"success": {"password": True}}
