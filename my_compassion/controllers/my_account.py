##############################################################################
#
#    Copyright (C) 2020-2023 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import secrets
from datetime import datetime, timedelta
from os import path, remove
from urllib.parse import urlencode
from zipfile import ZipFile

from passlib.context import CryptContext
from werkzeug.exceptions import NotFound

from odoo import _, fields
from odoo.exceptions import AccessDenied, UserError
from odoo.http import local_redirect, request, route

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.web.controllers.main import content_disposition

from .auto_texts import CHRISTMAS_TEXTS

IMG_URL = "/web/image/compassion.child.pictures/{id}/fullshot/"

# Avoids fetching too many donations in the portal
HISTORY_LIMIT = 1000


def _get_user_children(state=None):
    env = request.env
    partner = env.user.partner_id
    return _get_sponsorships(partner, state).mapped("child_id").sorted("preferred_name")


def _get_sponsorships(partner, state=None):
    """
    Find all the sponsorships of the given user.
    There is the possibility to fetch either only active sponsorships or only those
    that are terminated / cancelled. By default, all sponsorships are returned

    :return: a recordset of recurring.contract of the given user
    """
    env = request.env
    end_reason_child_depart = env.ref("sponsorship_compassion.end_reason_depart")

    def filter_sponsorships(sponsorship):
        can_show = True
        is_active = sponsorship.state not in ["draft", "cancelled", "terminated"]
        is_recent_terminated = (
            sponsorship.state == "terminated"
            and sponsorship.can_write_letter
            and sponsorship.end_reason_id == end_reason_child_depart
        )
        exit_communication_sent = (
            sponsorship.state == "terminated" and sponsorship.sds_state != "sub_waiting"
        )

        if state == "active":
            can_show = is_active or is_recent_terminated and not exit_communication_sent
        elif state == "terminated":
            can_show = (
                sponsorship.state == "terminated"
                and not is_recent_terminated
                or exit_communication_sent
            )
        elif state == "write":
            can_show = sponsorship.can_write_letter

        return can_show

    return (
        partner.get_portal_sponsorships()
        .with_context(allow_during_suspension=True)
        .filtered(filter_sponsorships)
    )


def _fetch_images_from_child(child):
    """
    Pass through the pictures of the child given as parameter and fills up a
    list of tuples of the form (image, full_path). Here, image is a record and
    full_path is the complete path of the image in the future archive.
    :param child: the child for which we want to create the image list
    :return: a list of tuples of the form (image, full_path)
    """
    images = []
    for image in child.pictures_ids:
        ext = image.image_url.split(".")[-1]
        filename = f"{child.preferred_name}_{image.date}_{child.local_id}.{ext}"
        folder = f"{child.preferred_name}_{child.local_id}"
        full_path = path.join(folder, filename)
        images.append((image, full_path))
    return images


def _create_archive(images, archive_name):
    """
    Create an archive from a list of images and the name of the future archive.
    Some files are created locally but are deleted after they are used by the
    method.
    :param images: a list of tuples of the form [(image1, full_path1), ...]
    :param archive_name: the name of the future archive
    :return: a response for the client to download the created archive
    """
    with ZipFile(archive_name, "w") as archive:
        for img, full_path in images:
            filename = path.basename(full_path)
            with open(filename, "wb") as image_file:
                image_file.write(base64.b64decode(img.fullshot))
            archive.write(filename, full_path)
            remove(filename)

    # Get binary content of the archive, then delete the latter
    with open(archive_name, "rb") as archive:
        zip_data = archive.read()
    remove(archive_name)

    return request.make_response(
        zip_data,
        [
            ("Content-Type", "application/zip"),
            ("Content-Disposition", content_disposition(archive_name)),
        ],
    )


def _single_image_response(image):
    return request.redirect(IMG_URL.format(id=image.id) + "?download=true")


def _download_image(child_id, obj_id):
    """
    Download one or multiple images (in a .zip archive if more than one) and
    return a response for the user to download it.
    :param obj_id: the id of the image to download or None
    :param child_id: the id of the child to download from or None
    :return: A response for the user to download a single image or an archive
    containing multiples
    """
    # All children, all images
    if child_id < 0 and obj_id < 0:
        images = []
        for child in _get_user_children():
            images += _fetch_images_from_child(child)
        filename = "my_children_pictures.zip"
        return _create_archive(images, filename)

    if child_id < 0:
        return False

    # One child
    child = request.env["compassion.child"].browse(child_id)

    # All images from a child
    if child and obj_id < 0:
        images = _fetch_images_from_child(child)
        filename = f"{child.preferred_name}_{child.local_id}.zip"
        return _create_archive(images, filename)

    # A single image from a child
    if child and obj_id > 0:
        image = child.sudo().pictures_ids.filtered(lambda p: p.id == obj_id)
        return _single_image_response(image)

    return False


class MyAccountController(CustomerPortal):
    @route(
        "/my/login/<partner_uuid>/<redirect_page>",
        type="http",
        auth="public",
        website=True,
    )
    def magic_login(self, partner_uuid=None, redirect_page=None, **kwargs):
        """
        This route is used to log in a user with a magic link. The link is
        composed of the partner's uuid and the page to redirect to after the
        login. The partner is searched and if he exists, a user is created for
        him if he doesn't have one already. Then, the user is logged in and
        redirected to the page asked.
        @param partner_uuid: <str> the uuid of the partner
        @param redirect_page: <str> the page to redirect to after the login
        @param kwargs: additional optional arguments
        """
        if not partner_uuid:
            return None

        res_partner = request.env["res.partner"].sudo()
        res_users = request.env["res.users"].sudo()

        partner = res_partner.search([["uuid", "=", partner_uuid]], limit=1)
        partner = partner.sudo()

        redirect_page_request = local_redirect(f"/my/{redirect_page}", kwargs)

        if not partner:
            # partner does not exist
            return redirect_page_request

        user = res_users.search([["partner_id", "=", partner.id]], limit=1)

        if user and not user.created_with_magic_link:
            # user already have an account not created with the magic link
            # this will ask him to log in then redirect him on the route asked
            return redirect_page_request

        if not user:
            # don't have a res_user must be created
            login = MyAccountController._create_magic_user_from_partner(partner)
        else:
            # already have a res_user created with a magic link
            login = user.login

        MyAccountController._reset_password_and_authenticate(login)

        return redirect_page_request

    @staticmethod
    def _reset_password_and_authenticate(login):
        # create a random password
        password = secrets.token_urlsafe(16)

        # reset password
        crypt_context = CryptContext(
            schemes=["pbkdf2_sha512", "plaintext"], deprecated=["plaintext"]
        )
        password_encrypted = crypt_context.encrypt(password)
        request.env.cr.execute(
            "UPDATE res_users SET password=%s WHERE login=%s;",
            [password_encrypted, login],
        )
        request.env.cr.commit()

        # authenticate
        request.session.authenticate(request.session.db, login, password)
        return True

    @staticmethod
    def _create_magic_user_from_partner(partner):
        res_users = request.env["res.users"].sudo()

        values = {
            # ensure a login when the partner doesnt have an email
            "login": partner.email or "magic_login_" + secrets.token_urlsafe(16),
            "partner_id": partner.id,
            "created_with_magic_link": True,
        }

        # create a signup_token and create the account
        partner.signup_prepare()
        _, login, _ = res_users.signup(values=values, token=partner.signup_token)
        return login

    @route(["/my", "/my/home"], type="http", auth="user", website=True)
    def home(self, redirect=None, **post):
        # All this paths needs to be redirected
        partner = request.env.user.partner_id
        if partner.sponsorship_ids:
            return request.redirect("/my/children")
        else:
            return request.redirect("/my/information")

    @route("/my/letter", type="http", auth="user", website=True)
    def my_letter(self, child_id=None, template_id=None, **kwargs):
        """
        The route to write new letters to a selected child
        :param child_id: the id of the selected child
        :param template_id: the id of the selected template
        :param kwargs: additional arguments (optional)
        :return: a redirection to a webpage
        """
        children = _get_user_children("write")
        if len(children) == 0:
            return request.render("my_compassion.sponsor_a_child", {})

        if not child_id:
            return request.redirect(
                f"/my/letter?child_id={children[0].id}&template_id={template_id or ''}"
                f"&{urlencode(kwargs)}"
            )

        child = children.filtered(lambda c: c.id == int(child_id))
        if not child:  # The user does not sponsor this child_id
            return request.redirect(f"/my/letter?child_id={children[0].id}")
        templates = (
            request.env["correspondence.template"]
            .search(
                [
                    ("active", "=", True),
                    ("website_published", "=", True),
                ]
            )
            .sorted(lambda t: "0" if "christmas" in t.name else t.name)
        )
        if not template_id and len(templates) > 0:
            template_id = templates[0].id
        template = templates.filtered(lambda t: t.id == int(template_id))
        auto_texts = {}
        if "auto_christmas" in kwargs:
            for c in children:
                auto_texts[c.id] = CHRISTMAS_TEXTS.get(
                    c.field_office_id.primary_language_id.code_iso,
                    CHRISTMAS_TEXTS["eng"],
                ) % (c.preferred_name, request.env.user.partner_id.firstname)
        return request.render(
            "my_compassion.letter_page_template",
            {
                "child_id": child,
                "template_id": template,
                "children": children,
                "templates": templates,
                "partner": request.env.user.partner_id,
                "auto_texts": auto_texts,
            },
        )

    @route("/my/children", type="http", auth="user", website=True)
    def my_child(self, state="active", child_id=None, **kwargs):
        """
        The route to see all the partner's children information
        :param state: the state of the children's sponsorships (active or
        terminated)
        :param child_id: the id of the child
        :param kwargs: optional additional arguments
        :return: a redirection to a webpage
        """
        actives = _get_user_children("active")
        terminated = _get_user_children("terminated") - actives

        display_state = True
        # User can choose among groups if none of the two is empty
        if len(actives) == 0 or len(terminated) == 0:
            display_state = False

        # We get the children group that we want to display
        if state == "active" and len(actives) > 0:
            children = actives
        else:
            children = terminated
            state = "terminated"

        # No sponsor children
        if len(children) == 0:
            return request.render("my_compassion.sponsor_a_child", {})

        # No child is selected, we pick the first one by default
        if not child_id:
            return request.redirect(f"/my/children?child_id={children[0].id}")

        # A child is selected
        child = children.filtered(lambda c: c.id == int(child_id))

        # The user does not sponsor this child_id
        if not child:
            return request.redirect(
                f"/my/children?state={state}&child_id={children[0].id}"
            )

        # This child is sponsored by this user and is selected
        partner = request.env.user.partner_id
        correspondence_obj = request.env["correspondence"]
        correspondent = partner

        if partner.portal_sponsorships == "all_info":
            correspondent |= child.sponsorship_ids.filtered(
                lambda x: x.is_active
            ).mapped("correspondent_id")
            correspondence_obj = correspondence_obj.sudo()

        letters = correspondence_obj.search(
            [
                ("partner_id", "in", correspondent.ids),
                ("child_id", "=", int(child_id)),
                "|",
                "&",
                ("direction", "=", "Supporter To Beneficiary"),
                ("state", "!=", "Quality check unsuccessful"),
                "&",
                "&",
                ("state", "=", "Published to Global Partner"),
                ("letter_image", "!=", False),
                "|",
                ("communication_id", "=", False),
                ("sent_date", "!=", False),
            ],
            order="scanned_date DESC",
        )
        gift_categ = request.env.ref("sponsorship_compassion.product_category_gift")
        lines = (
            request.env["account.move.line"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("payment_state", "=", "paid"),
                    ("contract_id.child_id", "=", child.id),
                    ("product_id.categ_id", "=", gift_categ.id),
                    ("price_total", "!=", 0),
                ]
            )
        )
        request.session["child_id"] = child.id

        wordpress = (
            request.env["wordpress.configuration"].sudo().get_config(raise_error=False)
        )
        partner_profile_info = {
            "child_ref": child.local_id,
            "pname": partner.firstname + " " + partner.lastname,
            "pstreet": partner.street,
            "pzip": partner.zip,
            "pcity": partner.city,
            "pcountry": partner.country_id.name,
            "email": partner.email,
            # Add any other fields you want to prefill in the form
        }
        # Construct query string with user profile info
        query_string = urlencode(partner_profile_info)
        url_child_gift = (
            (f"https://{wordpress.host}{wordpress.child_gift_url}?{query_string}")
            if wordpress and partner_profile_info
            else "#"
        )

        context = {
            "child_id": child,
            "children": children,
            "letters": letters,
            "lines": lines,
            "state": state,
            "display_state": display_state,
            "url_child_gift": url_child_gift,
        }
        return request.render("my_compassion.my_children_page_template", context)

    @route(
        [
            "/my/donations",
            "/my/donations/page/<int:invoice_page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        """
        The route to the donations and invoicing page
        :param invoice_page: index of the invoice pagination
        :param invoice_per_page: the number of invoices to display per page
        :param form_id: the id of the filled form or None
        :param kw: additional optional arguments
        :return: a redirection to a webpage
        """
        partner = request.env.user.partner_id

        invoice_search_criteria = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]

        move_obj = request.env["account.move"].sudo()
        # invoice to show for the given pagination index
        all_invoices = move_obj.read_group(
            invoice_search_criteria,
            ["amount_total"],
            ["last_payment:day"],
            orderby="last_payment desc",
            limit=HISTORY_LIMIT,
        )
        offset = (invoice_page - 1) * invoice_per_page
        invoices_per_day = all_invoices[offset : offset + invoice_per_page]
        for invoice_group in invoices_per_day:
            # Agrement data for displaying all invoices
            invoices = move_obj.search(invoice_group["__domain"])
            invoice_group["description"] = invoices.get_my_account_display_name()
            invoice_group["last_payment"] = invoices[0].get_date(
                "last_payment", "d MMM yyyy"
            )
            invoice_group["amount"] = (
                f"{int(invoice_group['amount_total']):,d} "
                f"{invoices[0].currency_id.name}"
            )

        in_one_month = datetime.today() + timedelta(days=30)
        due_invoices = move_obj.search(
            [
                ("partner_id", "=", partner.id),
                ("payment_state", "=", "not_paid"),
                ("invoice_category", "=", "sponsorship"),
                ("move_type", "=", "out_invoice"),
                ("amount_total", "!=", 0),
                ("invoice_date", "<", fields.Date.to_string(in_one_month)),
            ]
        )

        sponsorships = _get_sponsorships(partner, state="active")
        currency = sponsorships.mapped("pricelist_id.currency_id")[:1].name

        # Dict of groups mapped to their sponsorships, and total amount
        # {group: (<sponsorships recordset>, total_amount string), ...}
        sponsorships_by_group = {}
        for g in sponsorships.mapped("group_id"):
            filtered_sponsorships = sponsorships.filtered(lambda s: s.group_id == g)
            total = int(sum(filtered_sponsorships.mapped('total_amount')))
            sponsorships_by_group[g] = (filtered_sponsorships, f"{total:,d} {currency}")

        values = self._prepare_portal_layout_values()
        pager = request.website.pager(
            url=request.httprequest.path.partition("/page/")[0],
            total=len(all_invoices),
            page=invoice_page,
            step=invoice_per_page,
            url_args=kw,
        )
        values.update(
            {
                "partner": partner,
                "sponsorships_by_group": sponsorships_by_group,
                "invoices_per_day": invoices_per_day,
                "pager": pager,
                "due_invoices": due_invoices,
            }
        )
        return request.render("my_compassion.my_donations_page_template", values)

    @route("/my/information", type="http", auth="user", website=True)
    def my_information(self, form_id=None, privacy_policy=None, **kw):
        """
        The route to display the information about the partner
        :param form_id: the form that has been filled or None
        :param kw: the additional optional arguments
        :return: a redirection to a webpage
        """
        partner = request.env.user.partner_id
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "partner": partner,
            }
        )

        if privacy_policy == "accepted" and not partner.legal_agreement_date:
            partner.legal_agreement_date = datetime.now()

        return request.render("my_compassion.my_information_page_template", values)

    @route("/my/download/<source>", type="http", auth="user", website=True)
    def download_file(self, source, **kw):
        """
        The route to download a file, that is either the tax receipt or an
        image
        :param source: Tells whether we want an image or a tax receipt
        :param kw: the additional optional arguments
        :return: a response to download the file
        """
        if source == "picture":
            child_id = int(kw.get("child_id", -1))
            obj_id = int(kw.get("obj_id", -1))
            return _download_image(child_id, obj_id)
        else:
            raise NotFound()

    @route(
        "/my/letter/<model('compassion.child'):child>/<string:mode>",
        type="json",
        methods=["POST"],
        auth="user",
    )
    def my_letter_preview(self, child, mode):
        """
        This method is called by the app to retrieve a PDF preview of a letter.
        We get in the params the image and text and build a PDF from there via
        the PDF generator.
        :return: An URL pointing to the PDF preview of the generated letter
        """
        kwargs = request.jsonrequest
        body = kwargs.get("body")
        if not body:
            raise UserError(_("No text provided for the letter."))
        template_id = kwargs.get(
            "template_id", request.env.ref("sbc_compassion.default_template").id
        )
        datas = []
        for attached_file in kwargs.get("file_upl", []):
            if isinstance(attached_file, dict) and "data" in attached_file:
                datas.append(
                    (
                        0,
                        0,
                        {
                            "datas": attached_file["data"],
                            "name": attached_file["name"],
                        },
                    )
                )
        source = kwargs.get("source", "MyCompassion")
        gen_vals = {
            "name": f"{source}-{child.local_id}",
            "selection_domain": str(
                [
                    ("child_id.local_id", "=", child.local_id),
                    ("state", "not in", ["draft", "cancelled"]),
                ]
            ),
            "body": body,
            "template_id": int(template_id),
            "image_ids": datas,
            "source": kwargs.get("source"),
        }
        language = request.env["langdetect"].sudo().detect_language(body)
        if language:
            gen_vals["language_id"] = language.id
        try:
            generator_id = int(kwargs.get("generator_id"))
        except (ValueError, TypeError):
            generator_id = None
        gen = None
        if generator_id:
            gen = (
                request.env["correspondence.s2b.generator"]
                .sudo()
                .browse(generator_id)
                .exists()
            )
            if gen and gen.state != "done":
                gen.write(gen_vals)
            else:
                gen = None
        if not gen:
            gen = request.env["correspondence.s2b.generator"].sudo().create(gen_vals)
        gen.onchange_domain()
        # Only generate for one sponsorship! If the child was sponsored several times
        gen.sponsorship_ids = gen.sponsorship_ids[:1]
        gen.preview()
        web_base_url = request.httprequest.host_url
        if mode == "send":
            gen.generate_letters()
        return {
            "preview_url": f"{web_base_url}web/image/{gen._name}/{gen.id}/preview_pdf",
            "generator_id": gen.id,
        }

    def _update_password(self, old, new1, new2):
        # TODO: Delete me in Odoo 16.0
        # Fixes a bug present in Odoo < 16.0
        # Fix commit in Odoo repository:
        # https://github.com/odoo/odoo/commit/6fea44277edef8ae7058e7bae9c69e84a026cfb8
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
