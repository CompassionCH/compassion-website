##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import calendar
import json
import logging
from datetime import date

import babel

from odoo import _, fields, http
from odoo.exceptions import AccessError
from odoo.http import request

from .my2_children import MyCompassionChildrenController

_logger = logging.getLogger(__name__)


class MyCompassionCorrespondenceController(MyCompassionChildrenController):
    # Helper function to safely parse integers from query params
    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @http.route(
        [
            "/my2/children/letters",
            "/my2/children/letters/<model('compassion.child'):child>",
        ],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_child_letters_page(self, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id
        current_year = date.today().year

        # Filtering params
        page = self._safe_int(kwargs.get("page"), 1)
        year_from = self._safe_int(kwargs.get("year_from"), 1900)
        year_to = self._safe_int(kwargs.get("year_to"), current_year)
        month_from = self._safe_int(kwargs.get("month_from"), 1)
        month_to = self._safe_int(kwargs.get("month_to"), 12)
        letter_type = kwargs.get("type")
        sort_order = kwargs.get("sort", "newest")
        unread_filter = kwargs.get("unread", "all")
        nr_filters_applied = 0
        child_id = self._safe_int(kwargs.get("child_id"), None)
        child = request.env["compassion.child"].browse(child_id)

        # Build filter date range
        last_day = calendar.monthrange(year_to, month_to)[1]
        from_date = date(year_from, month_from, 1)
        to_date = date(year_to, month_to, last_day)

        # Build the domain of the filtering of the letters
        filter_domain = [("partner_id", "=", partner.id)]

        if child:
            try:
                self._check_sponsored_child_access(child)
                filter_domain.append(("child_id", "=", child.id))
                nr_filters_applied += 1
            except AccessError:
                child = None

        filter_domain.append(("create_date", ">=", from_date))
        filter_domain.append(("create_date", "<=", to_date))

        if unread_filter == "unread":
            filter_domain.append(("email_read", "=", False))
            nr_filters_applied += 1

        if (
            year_from > 1900
            or year_to < current_year
            or month_from > 1
            or month_to < 12
        ):
            nr_filters_applied += 1
        if letter_type:
            filter_domain.append(("direction", "=", letter_type))
            nr_filters_applied += 1

        order = "create_date DESC" if sort_order == "newest" else "create_date ASC"

        if sort_order == "oldest":
            nr_filters_applied += 1

        # Pagination setup
        letters_per_page = 12
        offset = (page - 1) * letters_per_page
        total_letters = request.env["correspondence"].search_count(filter_domain)
        total_pages = max(1, -(-total_letters // letters_per_page))

        # Without the context here the letters are marked as read by just
        # iterating trough them in the xml.
        correspondence_model = request.env["correspondence"].with_context(
            tracking_disable=True
        )

        letters = correspondence_model.search(
            filter_domain, order=order, offset=offset, limit=letters_per_page
        )

        # Month names in the current language
        lang = request.env.context.get("lang", partner.lang)
        locale = babel.Locale.parse(lang)
        months = [(i, locale.months["format"]["wide"][i]) for i in range(1, 13)]

        return request.render(
            "my_compassion.my2_child_letters_page",
            {
                "letters": letters,
                "filter_child": child,
                "current_year": current_year,
                "children_list": children_sponsored_by_partner,
                "current_page": page,
                "total_pages": total_pages,
                "filters": {
                    "year_from": year_from,
                    "year_to": year_to,
                    "month_from": month_from,
                    "month_to": month_to,
                    "type": letter_type,
                    "sort": sort_order,
                    "unread": unread_filter,
                },
                "nr_filters_applied": nr_filters_applied,
                "months": months,
            },
        )

    @http.route(
        '/my2/children/<model("compassion.child"):child>/'
        'letters/<model("correspondence"):correspondence>/mark_read',
        type="json",
        auth="user",
        methods=["POST"],
    )
    def mark_letter_as_read(self, child, correspondence):
        letter = request.env["correspondence"].search(
            [("id", "=", correspondence.id)], limit=1
        )
        if (
            letter.exists()
            and letter.child_id == child
            and letter.partner_id.id == request.env.user.partner_id.id
        ):
            if not letter.email_read:  # only set if not already read
                letter.email_read = fields.Datetime.now()
            return {"status": "success"}
        return {"status": "error", "message": "Not found or unauthorized"}

    @http.route(
        "/my2/children/letters/new",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_new_letter_page(self, **kwargs):
        partner = request.env.user.partner_id
        child_id = self._safe_int(kwargs.get("child_id"), None)
        child = request.env["compassion.child"].browse(child_id)

        try:
            self._check_sponsored_child_access(child)
        except AccessError:
            return request.redirect("/my2/children/")
        # Retrieve the letter templates
        templates = (
            request.env["correspondence.template"]
            .search(
                [
                    ("active", "=", True),
                    ("website_published", "=", True),
                ]
            )
            # Sort the templates alphabetically, placing "Christmas"
            # templates at the beginning
            # "0" is special sorting key because it comes
            # before any letter in ASCII order.
            .sorted(lambda t: "0" if "christmas" in t.name.lower() else t.name)
        )

        if not child:
            child = partner.sponsorship_ids[:1].child_id

        draft = (
            request.env["correspondence.s2b.generator"]
            .sudo()
            .search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("child_id", "=", child.id),
                    ("state", "in", ["draft", "preview"]),
                ],
                limit=1,
            )
            .with_context(bin_size=False)
        )

        return request.render(
            "my_compassion.my2_new_letter_page",
            {
                "selected_child": child,
                "sponsorship_ids": partner.sponsorship_ids,
                "templates": templates,
                "draft": draft,
            },
        )

    @http.route(
        "/my2/letter/remove_attachment",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def my2_remove_attachment(self, attachment_id):
        """

        Deletes an attachment linked to the draft letter of the logged-in user.
        Used by the × button in my2_new_letter_page.
        """
        try:
            attachment = request.env["ir.attachment"].sudo().browse(int(attachment_id))
            if not attachment.exists():
                return {"success": False, "error": _("Attachment not found")}

            draft = request.env["correspondence.s2b.generator"].search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("image_ids", "in", attachment.id),
                ],
                limit=1,
            )

            if not draft:
                return {"success": False, "error": _("Unauthorized")}

            attachment.unlink()

            return {"success": True}

        except (ValueError, TypeError) as e:
            _logger.warning("Failed to remove attachment %s: %s", attachment_id, e)
            return {"error": _("Something went wrong.")}

        """
        Deletes the draft letter generator for the given child and user.
        Used when the user clicks ont hte "Start Over" button in my2_new_letter_page.
        """

    @http.route(
        "/my2/letter/unlink_draft_generator",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def unlink_draft_generator(self, child_id):
        try :
            child = request.env["compassion.child"].browse(child_id)
            self._check_sponsored_child_access(child)
        except (AccessError, ValueError, TypeError) as e:
            _logger.warning(
                "Failed to unlink draft generator for child %s: %s", child_id, e
            )
            return {"error": _("Something went wrong.")}

        
        drafts = (
            request.env["correspondence.s2b.generator"]
            .sudo()
            .search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("child_id", "=", child_id),
                    ("state", "in", ["draft", "preview"]),
                ]
            )
        )
        drafts.unlink()
        return {"success": True}

    @http.route(
        "/my2/children/letters/create_generator",
        type="json",
        auth="user",
        methods=["POST"],
        sitemap=False,
    )
    def my2_create_generator(self, **post):
        """
        Used in my2_new_letter.js for sending the new letter form data
        """
        try:
            child_id = int(post.get("child_id"))
            child = request.env["compassion.child"].browse(child_id)
            self._check_sponsored_child_access(child)
            template_id = int(post.get("template_id"))
        except (AccessError, ValueError, TypeError) as e:
            _logger.warning(
                "Failed to create letter generator for post %s: %s", post, e
            )
            return {"error": _("Something went wrong.")}

        attachments = [
            (0, 0, {"datas": file["content"], "name": file["filename"]})
            for file in post.get("attachments", [])
            if isinstance(file, dict) and "content" in file
        ]

        letter_values = {
            "name": f"{post.get('source')}-{child.local_id}",
            "body": post.get("letter_body"),
            "template_id": template_id,
            "image_ids": attachments,
            "source": post.get("source"),
            "child_id": child.id,
            "user_id": request.env.user.id,
            "state": "draft",
            # Restore initial generation status
            "generation_status": "creating_task",
            "generation_error_message": "",
        }
        generator_id = self._safe_int(post.get("generator_id"), 0)
        if generator_id:
            letter_generator = (
                request.env["correspondence.s2b.generator"].browse(generator_id).sudo()
            )
            letter_generator.write(letter_values)

        else:
            letter_generator = (
                request.env["correspondence.s2b.generator"].sudo().create(letter_values)
            )
        if not letter_generator.exists():
            return {"error": _("Something went wrong.")}
        letter_generator.set_sponsorship_from_user_and_child()

        # Define the steps for the progress bar
        # Format: (step_index, status_key, description)
        processing_steps = [
            (0, "create_task", _("Creating Task...")),
            (1, "apply_template", _("Applying Template...")),
            (2, "apply_text", _("Adding Your Text...")),
            (3, "apply_images", _("Adding Attachments...")),
            (4, "generate_pdf", _("Generating PDF...")),
            (5, "finalizing", _("Finalizing...")),
        ]

        return {
            "generator_id": letter_generator.id,
            "steps": processing_steps,  # Return the steps to the client
        }

    @http.route(
        "/my2/children/letters/launch_generation",
        type="json",
        auth="user",
        methods=["POST"],
        sitemap=False,
    )
    def my2_launch_letter_generation(self, **post):
        """
        Handles the launch of the letter generation process for a specific child.
        Args:
            post (dict): A dictionary containing the following keys:
                - "child_id" (int): The ID of the child to whom the letter is generated.
                - "generator_id" (int): The ID of the letter generator instance.

        Returns:
            dict: A dictionary containing:
                - "preview_url" (str): The URL to preview the generated letter PDF.
                - "generator_id" (int): The ID of the letter generator instance.

        Raises:
            AccessError: If the user does not have access to the specified child.
            ValueError/TypeError: If invalid data is provided in the request.

        Used in my2_new_letter.js
        """
        try:
            generator = (
                request.env["correspondence.s2b.generator"]
                .sudo()
                .browse(int(post.get("generator_id")))
            )
            generator.ensure_one()
        except (AccessError, ValueError, TypeError) as e:
            _logger.warning(
                "Failed to launch letter generation for post %s: %s", post, e
            )
            return {
                "error": _(
                    "We couldn't find your letter. Please try reloading the page."
                )
            }

        if post.get("mode") == "preview":
            generator.preview()

        elif post.get("mode") == "send":
            # Run a preview to check if the letter's length is acceptable
            generator.preview()
            if generator.generation_status != "failed":
                generator.isolated_write({"generation_status": "finalizing"})
                generator.generate_letters_job()
        if generator.generation_status == "failed":
            return {"error": generator.generation_error_message}

        generator.isolated_write({"generation_status": "done"})

        return {
            "preview_url": f"{request.httprequest.host_url}web/image"
            f"/{generator._name}/{generator.id}/preview_pdf",
            "generator_id": generator.id,
        }

    @http.route(
        "/my2/children/letters/status",
        type="json",
        auth="user",
        methods=["POST"],
        sitemap=False,
    )
    def my2_get_letter_status(self, **post):
        """
        Endpoint for the frontend to poll for the generation status.
        Used in my2_new_letter.js
        """
        try:
            child_id = int(post.get("child_id"))
            child = request.env["compassion.child"].browse(child_id)
            self._check_sponsored_child_access(child)

            generator_id = int(post.get("generator_id"))
            letter_generator = (
                request.env["correspondence.s2b.generator"].sudo().browse(generator_id)
            )
            if not letter_generator.exists():
                return {"status": "failed", "error": _("Generator not found.")}

            status = letter_generator.generation_status

            if status == "done":
                # If done, also return the final data needed by the frontend
                return {
                    "status": "done",
                    "result": {
                        "preview_url": f"{request.httprequest.host_url}web/image"
                        f"/{letter_generator._name}/{letter_generator.id}/preview_pdf",
                        "generator_id": letter_generator.id,
                    },
                }
            else:
                if status == "failed":
                    return {
                        "status": status,
                        "error": letter_generator.generation_error_message,
                    }
                return {"status": status}

        except (AccessError, ValueError, TypeError) as e:
            _logger.warning("Failed to get letter status for post %s: %s", post, e)
            return {"status": "failed", "error": _("Access denied or invalid ID.")}

    @http.route(
        "/my2/children/letter/templates",
        type="http",
        auth="user",
        website=True,
    )
    def get_letter_templates(self, **kw):
        """
        This controller returns the currently active letter template.
        """

        templates = (
            request.env["correspondence.prewritten.letter"]
            .sudo()
            .search([("status", "=", "active")], limit=1)
        )

        template_text = templates.text or ""
        if template_text:
            partner = request.env.user.partner_id
            child = request.env["compassion.child"]
            try:
                child_id = self._safe_int(kw.get("child_id"), False)
                if child_id:
                    child = request.env["compassion.child"].browse(child_id)
                    child.exists().ensure_one()
                    self._check_sponsored_child_access(child)
            except (AccessError, ValueError):
                _logger.warning("Invalid child access for letter template.")
            replacements = {
                "%child%": child.preferred_name or "",
                "%firstname%": partner.preferred_name or partner.name or "",
                "%lastname%": partner.lastname or "",
            }
            for old, new in replacements.items():
                template_text = template_text.replace(old, new)

        data = {
            "template_text": template_text,
        }

        return request.make_response(
            json.dumps(data), headers=[("Content-Type", "application/json")]
        )
