##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nicolò Hepp <nhepp@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import date

from odoo import _, api, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import html_escape


class MyCompassionUserController(http.Controller):
    @http.route("/my2/user_settings", type="http", auth="user", website=True)
    def render_user_settings_page(self, **kwargs):
        partner = request.env.user.partner_id

        # Pre-fetch data for the template's selection fields.
        titles = (
            request.env["res.partner.title"]
            .sudo()
            .search([("is_shown_on_public_forms", "=", True)])
        )
        countries = request.env["res.country"].sudo().search([])

        # Determines which tab should be active when the page loads.
        current_tab = request.params.get("current_tab", "personal-information")

        return request.render(
            "my_compassion.my2_user_settings_page",
            {
                "user": request.env.user,
                "partner": partner,
                "titles": titles,
                "countries": countries,
                "current_tab": current_tab,
            },
        )

    @http.route(
        "/my2/user_settings/set_personal_info",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def set_personal_info(self, **post):
        partner = request.env.user.partner_id
        # A whitelist of fields that are allowed to be updated through this endpoint.
        allowed_fields = {
            "title": int,
            "lastname": str,
            "firstname": str,
            "street": str,
            "city": str,
            "country_id": int,
            "zip": str,
            "mobile": str,
            "phone": str,
            "email": str,
        }

        optional_fields = {"phone", "mobile"}

        vals_to_update = {}
        errors = {}
        # Iterate through submitted data and validate it against the allowed fields.
        for field, value in post.items():
            if field in allowed_fields:
                clean_value = (value or "").strip()
                if not clean_value and field not in optional_fields:
                    errors[field] = _("This field cannot be empty.")
                else:
                    try:
                        vals_to_update[field] = allowed_fields[field](clean_value)
                    except (ValueError, TypeError):
                        errors[field] = _("Invalid value.")

        if errors:
            # If any errors were found, return them to the frontend,
            # do not update the record.
            return {"success": False, "errors": errors}

        if vals_to_update:
            # When an address component is changed, reset the linked zip_id
            if any(k in vals_to_update for k in ["city", "zip", "country_id"]):
                vals_to_update["zip_id"] = False

            # getting old values for email notification of the changes
            old_values = {f: getattr(partner, f) for f in vals_to_update.keys()}

            try:
                partner.sudo().write(vals_to_update)
            except ValidationError as e:
                if "email" in vals_to_update:
                    return {"success": False, "errors": {"email": e.args[0]}}

            new_values = {f: getattr(partner, f) for f in vals_to_update.keys()}

            # Prepare change summary for notification
            changes = []
            for field in vals_to_update.items():
                # those are compute
                if field in ("zip_id", "email_bounced", "preferred_name"):
                    continue

                old_val = old_values.get(field)
                new_val = new_values.get(field)

                # transforming the database values to a user-friendly
                # format for the staff
                if field in ("title", "country_id"):
                    old_val_userfriendly = old_val.name if old_val else ""
                    new_val_userfriendly = new_val.name if new_val else ""
                else:
                    old_val_userfriendly = str(old_val or "")
                    new_val_userfriendly = str(new_val or "")

                if old_val_userfriendly != new_val_userfriendly:
                    changes.append(
                        f"<li><b>{field}</b>: {html_escape(old_val_userfriendly)} → "
                        f"{html_escape(new_val_userfriendly)}</li>"
                    )

            if changes:
                body_html = (
                    f"<p>Sponsor <b>{html_escape(partner.name)}</b>, "
                    f"with user_id <b>{partner.id}</b> "
                    f"has updated their personal information via MyCompassion. "
                    f"Please review the changes:</p>"
                    f"<ul>{''.join(changes)}</ul>"
                )

                # Send the notification email
                mail_values = {
                    "subject": f"Partner data change - {partner.name} "
                    f"(Ref {partner.ref})",
                    "body_html": body_html,
                    # TODO : replace with a setting in v17
                    "email_to": "sds_requests@compassion.ch",
                }
                request.env["mail.mail"].sudo().create(mail_values)

        return {"success": True}

    @http.route(
        "/my2/user_settings/set_account_settings",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def set_account_settings(self, **post):
        user = request.env.user
        new_login = (post.get("login") or "").strip()

        if not new_login:
            return {"success": False, "errors": {"login": _("Login cannot be empty.")}}

        # Check if login is already taken by another user
        if (
            request.env["res.users"]
            .sudo()
            .search_count([("login", "=", new_login), ("id", "!=", user.id)])
        ):
            return {
                "success": False,
                "errors": {
                    "login": _("This email is already used as a login by another user.")
                },
            }

        user.sudo().write({"login": new_login})
        return {"success": True}

    @http.route(
        "/my2/user_settings/agree_data_protection",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def agree_data_protection(self, **post):
        request.env.user.partner_id.sudo().write({"legal_agreement_date": date.today()})
        return {"success": True}

    @http.route(
        "/my2/user_settings/set_communication_settings",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def set_partner_communication_settings(self, **post):
        partner = request.env.user.partner_id
        # A whitelist of allowed communication preference fields.
        allowed_fields = {
            "opt_out",
            "tax_certificate",
            "letter_delivery_preference",
            "photo_delivery_preference",
            "birthday_reminder",
            "sponsorship_anniversary_card",
        }

        update_vals = {}
        for field, value in post.items():
            if field in allowed_fields:
                # Convert string booleans from JS
                if isinstance(value, bool):
                    update_vals[field] = value
                elif str(value).lower() in ["true", "false"]:
                    update_vals[field] = str(value).lower() == "true"
                else:
                    update_vals[field] = value

        if update_vals:
            partner.sudo().write(update_vals)

        return {"success": True}

    @http.route(
        "/my2/user_settings/delete_account",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def user_settings_page_delete_account(self):
        partner = request.env.user.partner_id
        if partner.has_sponsorships:
            return {
                "success": False,
                "error": _("Account cannot be deleted due to active sponsorships."),
            }
        try:
            request.env["res.partner"].with_user(api.SUPERUSER_ID).browse(
                partner.id
            ).forget_me()
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "error": _("Account could not be deleted, please contact us. ")
                + str(e),
            }
