##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import calendar
import time
from datetime import date

import babel

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

from .my2_children import MyCompassionChildrenController


class MyCompassionCorrespondenceController(MyCompassionChildrenController):
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
    def my2_render_child_letters_page(self, child=None, **kwargs):
        partner = request.env.user.partner_id
        children_sponsored_by_partner = partner.sponsorship_ids.child_id
        current_year = date.today().year

        # Helper function to safely parse integers from query params
        def safe_int(value, default):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # Filtering params
        page = safe_int(kwargs.get("page"), 1)
        year_from = safe_int(kwargs.get("year_from"), 1900)
        year_to = safe_int(kwargs.get("year_to"), current_year)
        month_from = safe_int(kwargs.get("month_from"), 1)
        month_to = safe_int(kwargs.get("month_to"), 12)
        letter_type = kwargs.get("type")
        sort_order = kwargs.get("sort", "newest")
        unread_filter = kwargs.get("unread")
        nr_filters_applied = 0

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

        if unread_filter == "true":
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
                },
                "nr_filters_applied": nr_filters_applied,
                "months": months,
            },
        )

    @http.route(
        "/my2/children/<model('compassion.child'):child>/letter/new",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_new_letter_page(self, child, **kwargs):
        partner = request.env.user.partner_id
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

        breadcrumbs = [
            {"name": "Children", "url": "/my2/children/", "active": False},
            {
                "name": "New Letter",
                "url": "/my2/children/" + str(child.id) + "/letter/new",
                "active": True,
            },
        ]

        return request.render(
            "my_compassion.my2_new_letter_page",
            {
                "selected_child": child,
                "sponsorship_ids": partner.sponsorship_ids,
                "templates": templates,
                "breadcrumbs": breadcrumbs,
            },
        )

    @http.route(
        "/my2/children/letter/new",
        type="json",
        auth="user",
        methods=["POST"],
        sitemap=False,
    )
    def my2_create_new_letter(self, **post):
        """
        Used in my2_new_letter.js for sending the new letter form data
        """
        try:
            child_id = int(post.get("child_id"))
            child = request.env["compassion.child"].browse(child_id)
            self._check_sponsored_child_access(child)
            template_id = int(post.get("template_id"))
        except (AccessError, ValueError, TypeError):
            return {"error": "Something went wrong."}

        attachments = [
            (0, 0, {"datas": file["content"], "name": file["filename"]})
            for file in post.get("attachments", [])
            if isinstance(file, dict) and "content" in file
        ]

        letter_values = {
            "name": f"{post.get('source')}-{child.local_id}",
            "selection_domain": str(
                [
                    ("child_id.local_id", "=", child.local_id),
                    ("state", "not in", ["draft", "cancelled"]),
                ]
            ),
            "body": post.get("letter_body"),
            "template_id": template_id,
            "image_ids": attachments,
            "source": post.get("source"),
        }

        letter_generator = (
            request.env["correspondence.s2b.generator"].sudo().create(letter_values)
        )
        if not letter_generator:
            return {"error": "Something went wrong."}

        self.process_letter_generator(
            letter_generator=letter_generator, post=post.copy()
        )

        return {
            "preview_url": f"{request.httprequest.host_url}web/image"
            f"/{letter_generator._name}/{letter_generator.id}/preview_pdf",
            "letter_values": letter_values,
            "generator_id": letter_generator.id,
        }

    @http.route(
        "/my2/children/letter/create_generator",
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
        except (AccessError, ValueError, TypeError):
            return {"error": "Something went wrong."}

        attachments = [
            (0, 0, {"datas": file["content"], "name": file["filename"]})
            for file in post.get("attachments", [])
            if isinstance(file, dict) and "content" in file
        ]

        letter_values = {
            "name": f"{post.get('source')}-{child.local_id}",
            "selection_domain": str(
                [
                    ("child_id.local_id", "=", child.local_id),
                    ("state", "not in", ["draft", "cancelled"]),
                ]
            ),
            "body": post.get("letter_body"),
            "template_id": template_id,
            "image_ids": attachments,
            "source": post.get("source"),
        }

        letter_generator = (
            request.env["correspondence.s2b.generator"].sudo().create(letter_values)
        )
        if not letter_generator:
            return {"error": "Something went wrong."}

        return {
            "generator_id": letter_generator.id,
        }

    @http.route(
        "/my2/children/letter/launch_generation",
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
            child_id = int(post.get("child_id"))
            child = request.env["compassion.child"].browse(child_id)
            self._check_sponsored_child_access(child)
        except (AccessError, ValueError, TypeError):
            return {"error": "Something went wrong."}

        letter_generator_id = post.get("generator_id")
        if not letter_generator_id:
            return {"error": "Something went wrong."}
        letter_generator = (
            request.env["correspondence.s2b.generator"]
            .sudo()
            .browse(letter_generator_id)
        )
        if not letter_generator.exists():
            return {"error": "Something went wrong."}

        # Define callbacks for each stage of the process
        # These callbacks update the generation_status field and commit in the db.
        callbacks = {
            "create_letter_callback": lambda: (
                letter_generator.write({"generation_status": "creating_task"}),
                request.env.cr.commit(),
            ),
            "apply_template_callback": lambda: (
                letter_generator.write({"generation_status": "apply_template"}),
                request.env.cr.commit(),
            ),
            "apply_text_callback": lambda: (
                letter_generator.write({"generation_status": "apply_text"}),
                request.env.cr.commit(),
            ),
            "apply_img_callback": lambda: (
                letter_generator.write({"generation_status": "apply_images"}),
                request.env.cr.commit(),
            ),
            "generating_pdf_callback": lambda: (
                letter_generator.write({"generation_status": "generate_pdf"}),
                request.env.cr.commit(),
            ),
            "failure_callback": lambda: (
                letter_generator.write({"generation_status": "failed"}),
                time.sleep(10),
                request.env.cr.commit(),
            ),
            "finalizing_callback": lambda: (
                letter_generator.write({"generation_status": "finalizing"}),
                time.sleep(3),
                request.env.cr.commit(),
            ),
        }
        # Launch the processing of the letter generator with the defined callbacks
        self.process_letter_generator(letter_generator, post=post, callbacks=callbacks)

        (letter_generator.write({"generation_status": "done"}),)
        request.env.cr.commit()
        return {
            "preview_url": f"{request.httprequest.host_url}web/image"
            f"/{letter_generator._name}/{letter_generator.id}/preview_pdf",
            "generator_id": letter_generator.id,
        }

    @http.route(
        "/my2/children/letter/status",
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
                return {"status": "failed", "error": "Generator not found."}

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
                return {"status": status}

        except (AccessError, ValueError, TypeError):
            return {"status": "failed", "error": "Access denied or invalid ID."}

    def process_letter_generator(self, letter_generator, post, callbacks=None):
        """
        Processes the letter generator by executing its domain change, preview,
        and letter generation logic. This method orchestrates the entire
        generation flow, using a system of callbacks to report progress or
        handle failures.

        Args:
            letter_generator (object): The `correspondence.s2b.generator`
                record to process.
            post (dict): A dictionary containing data from the client request.
                It is expected to include a "mode" key ('send' or 'preview')
                to determine the full operation.
            callbacks (dict, optional): A dictionary of callable functions that
                are triggered at various stages of the process. This is used
                to provide real-time feedback. Defaults to None.
                Expected keys include:
                - 'create_letter_callback': Called at the very beginning of
                  the PDF generation process within `preview`.
                - 'apply_template_callback': Called when the base template is
                  being applied.
                - 'apply_text_callback': Called when the letter's text body is
                  being rendered onto the template.
                - 'apply_img_callback': Called when attachments or images are
                  being added to the letter.
                - 'generating_pdf_callback': Called before the final PDF is compiled.
                - 'finalizing_callback': Called before the final
                - 'failure_callback': Called if any exception occurs during
                  the entire process.

        Raises:
            Exception: Re-raises any exception encountered during the process
                       after invoking the 'failure_callback', if provided. This
                       ensures the error propagates up the call stack.
        """
        try:
            letter_generator.onchange_domain()
            letter_generator.preview(**(callbacks or {}))

            if post.get("mode") == "send":
                if callbacks and "finalizing_callback" in callbacks:
                    callbacks["finalizing_callback"]()
                letter_generator.generate_letters_job()

        except Exception:
            if callbacks and "failure_callback" in callbacks:
                callbacks["failure_callback"]()
            raise
