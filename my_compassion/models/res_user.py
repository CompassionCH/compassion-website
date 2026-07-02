##############################################################################
#
#    Copyright (C) 2021 Compassion CH (http://www.compassion.ch)
#    @author: Jonathan guerne <guernej@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.auth_signup.models.res_partner import now

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    created_with_magic_link = fields.Boolean(default=False)

    def reset_password(self, login):
        """retrieve the user corresponding to login (login or email),
        and reset their password

        case insensitive for email matching
        """
        try:
            return super().reset_password(login)
        except Exception:
            users = self.search([("email", "=ilike", login)])
            if len(users) != 1:
                raise
            return users.action_reset_password()

    def _find_and_replace_partner_async(self, user_id, email):
        """Asynchronously find an existing partner by email and link it to the user,
        removing the default partner (created in the signup) if necessary.
        """

        self = self.sudo()
        user = self.env["res.users"].browse(user_id)

        # Ensure the user exists and is valid
        if not user.exists():
            _logger.error("User with ID %s no longer exists. Task aborted.", user_id)
            return

        old_partner = user.partner_id
        selected_partner = old_partner  # By default, keep the current partner

        # Check for other partners with the same email
        partners = self.env["res.partner"].search(
            [("email", "=", email), ("id", "!=", old_partner.id)]
        )

        if partners:
            # Select the best existing partner
            selected_partner = partners.sorted(
                key=lambda partner: (
                    partner.number_sponsorships,
                    partner.write_date or partner.create_date,
                ),
                reverse=True,
            )[0]
            user.write({"partner_id": selected_partner.id})
            _logger.info(
                "User %s linked to existing partner %s asynchronously.",
                user.login,
                selected_partner.name,
            )
            selected_partner.signup_type = old_partner.signup_type
            selected_partner.signup_token = old_partner.signup_token
            selected_partner.signup_expiration = old_partner.signup_expiration
            selected_partner.signup_url = old_partner.signup_url
            old_partner.unlink()
            _logger.info("Partner deleted.")

            _logger.info(
                "User %s linked to existing partner %s asynchronously.",
                user.login,
                selected_partner.name,
            )
        else:
            # No better partner found
            _logger.info("No other partner found for user %s.", user.login)

        self.env.flush_all()

    @api.model
    def signup(self, values, token=None):
        """Override the signup process to include business
        logic for linking existing partners.
        After creating a new user and partner, ensure that users
        are properly linked to existing partners based on their email.
        """
        # This is not a valid user field but is used for legal agreements
        values.pop("privacy_policy", None)

        # Call the superclass's signup method
        dbname, login, password = super().signup(values, token)

        if not token:
            email = values.get("email") or values.get("login")

            # Retrieve the newly created user
            user = self.search([("login", "=", login)], limit=1)
            if not user:
                _logger.error(
                    "Signup failed: No user found with login '%s' after signup.", login
                )
                return dbname, login, password  # Or handle as appropriate

            # Ensure changes are flushed and committed before scheduling the job
            self.env.flush_all()

            # Queue the task to find or replace the partner
            self.with_delay_sh(
                "_find_and_replace_partner_async", user.id, email, priority=5
            )
            _logger.info(
                "Async task to find and replace partner for user %s queued.",
                user.login,
            )

        return dbname, login, password

    def action_reset_password(self):
        """Create signup token for each user and send their signup URL
        by creating a communication job.
        Called only when user is created. Not when reseting password
        """
        if self.env.context.get("install_mode", False):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))

        # Prepare reset password signup
        create_mode = bool(self.env.context.get("create_user"))
        expiration = False if create_mode else now(days=+1)
        self.mapped("partner_id").signup_prepare(
            signup_type="reset", expiration=expiration
        )

        # Retrieve the communication config
        comm_config = self.env.ref(
            "my_compassion.user_account_confirmation", raise_if_not_found=False
        )
        if not comm_config:
            raise UserError(_("Communication configuration is missing."))

        for user in self:
            partner = user.partner_id
            if not partner.email:
                raise UserError(
                    _(
                        "Cannot send email: the partner %s has no email address.",
                        partner.name,
                    )
                )

            try:
                # Create the job and send the email
                self.env["partner.communication.job"].create(
                    {
                        "partner_id": partner.id,
                        "config_id": comm_config.id,
                        "auto_send": True,
                    }
                )

            except Exception as e:
                _logger.error(
                    "Failed to send account confirmation email for user %s: %s",
                    user.login,
                    e,
                )
                raise UserError(_("An error occurred.")) from e

            _logger.info(
                "Password reset job created for user <%s> to <%s>",
                user.login,
                partner.email,
            )
