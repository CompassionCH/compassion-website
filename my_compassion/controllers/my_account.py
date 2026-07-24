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
from datetime import datetime
from os import path, remove
from urllib.parse import urlencode
from zipfile import ZipFile

from passlib.context import CryptContext
from werkzeug.exceptions import NotFound

from odoo import _
from odoo.exceptions import UserError
from odoo.http import content_disposition, request, route

from odoo.addons.portal.controllers.portal import CustomerPortal

from .website_utils import resolve_host_my2_website, safe_int

IMG_URL = "/web/image/compassion.child.pictures/{id}/fullshot/"

# Avoids fetching too many donations in the portal
HISTORY_LIMIT = 1000


def _get_user_children(state=None):
    env = request.env
    partner = env.user.partner_id
    return (
        partner.get_portal_sponsorships(state)
        .mapped("child_id")
        .sorted("preferred_name")
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
        if not image.image_url:
            continue
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
            if not img.fullshot:
                continue
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
        "/my/login/<partner_uuid>/<path:redirect_page>",
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

        # Check if the requested page is already formatted for MyCompassion 2.0
        if redirect_page.startswith("my2/"):
            target = f"/{redirect_page}"
        else:
            # Handles dead redirections in case the link is from MyCompassion 1.0
            target = f"/my/{redirect_page}"
        if kwargs:
            target = f"{target}?{urlencode(kwargs)}"
        redirect_page_request = request.redirect(target)

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
        request.session.authenticate(
            request.session.db,
            {"login": login, "password": password, "type": "password"},
        )
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

    ############################# REDIRECTS ################################

    @route(["/my", "/my/home"], type="http", auth="user", website=True)
    def home(self, redirect=None, **post):
        """
        This is a dead route of MyCompassion 1.0
        From MyCompassion 2.0, we ensured a proper redirection
        for user using old links.
        Redirects only when the request host resolves to MyCompassion.
        """
        if resolve_host_my2_website():
            return request.redirect(redirect or "/my2/dashboard")

        return super().home(redirect=redirect, **post)

    @route("/my/letter", type="http", auth="user", website=True)
    def redirect_old_my_letter(self, child_id=None, template_id=None, **kwargs):
        """
        This is a dead route of MyCompassion 1.0
        From MyCompassion 2.0, we ensured a proper redirection
        for user using old links.
        """
        target = "/my2/children/letters/new"
        params = {}
        if child_id:
            params["child_id"] = child_id
        if template_id:
            params["template_id"] = template_id

        if params:
            target += f"?{urlencode(params)}"
        return request.redirect(target)

    @route("/my/children", type="http", auth="user", website=True)
    def redirect_old_my_child(self, state="active", child_id=None, **kwargs):
        """
        This is a dead route of MyCompassion 1.0
        From MyCompassion 2.0, we ensured a proper redirection
        for user using old links.
        """
        if child_id:
            return request.redirect(f"/my2/children/{child_id}")
        return request.redirect("/my2/children")

    @route(
        [
            "/my/donations",
            "/my/donations/page/<int:invoice_page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def redirect_old_my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        """
        This is a dead route of MyCompassion 1.0
        From MyCompassion 2.0, we ensured a proper redirection
        for user using old links.
        """
        return request.redirect("/my2/donations")

    @route("/my/information", type="http", auth="user", website=True)
    def redirect_old_my_information(self, form_id=None, privacy_policy=None, **kw):
        """
        This is a dead route of MyCompassion 1.0
        From MyCompassion 2.0, we ensured a proper redirection
        for user using old links.
        """
        if resolve_host_my2_website():
            return request.redirect("/my2/user_settings")

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

    @route(
        "/child/<string:child_identifier>/sponsor",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def redirect_old_child_sponsor(self, child_identifier, **kw):
        """
        This is a deprecated route of MyCompassion 1.0.
        From MyCompassion 2.0, we ensured a proper redirection
        for users using old links.
        """

        # If the URL provided is a basic integer (e.g., "241011"),
        # fetch the record with sudo() and convert it to a proper slug
        if child_identifier.isdigit():
            child_record = (
                request.env["compassion.child"].sudo().browse(int(child_identifier))
            )
            if child_record.exists():
                child_identifier = request.env["ir.http"]._slug(child_record)

        new_url = f"/my2/new-sponsorship/{child_identifier}"

        # Extract and append any query parameters (like UTMs)
        query_string = request.httprequest.query_string.decode("utf-8")
        if query_string:
            new_url = f"{new_url}?{query_string}"

        return request.redirect(new_url, code=301)

    @route(
        [
            "/children",
            "/children/page/<int:page>",
            "/children/<string:random>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def redirect_old_public_children(self, page=1, random=False, **kw):
        """
        This is a deprecated route of MyCompassion 1.0.
        From MyCompassion 2.0, we ensured a proper redirection
        for users using old links.
        """
        new_url = "/my2/sponsorships"
        query_string = request.httprequest.query_string.decode("utf-8")
        if query_string:
            new_url = f"{new_url}?{query_string}"
        return request.redirect(new_url, code=301)

    @route(
        "/child/<string:child_ref>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def redirect_old_public_child(self, child_ref, **kw):
        """
        This is a deprecated route of MyCompassion 1.0.
        From MyCompassion 2.0, we ensured a proper redirection
        for users using old links.
        """
        if child_ref.isdigit():
            child_record = request.env["compassion.child"].sudo().browse(int(child_ref))
            if child_record.exists():
                child_ref = request.env["ir.http"]._slug(child_record)
        new_url = f"/my2/new-sponsorship/{child_ref}"
        query_string = request.httprequest.query_string.decode("utf-8")
        if query_string:
            new_url = f"{new_url}?{query_string}"
        return request.redirect(new_url, code=301)

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
            child_id = safe_int(kw.get("child_id"), -1)
            obj_id = safe_int(kw.get("obj_id"), -1)
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
        kwargs = request.get_json_data()
        body = kwargs.get("body")
        if not body:
            raise UserError(_("No text provided for the letter."))
        default_template_id = request.env.ref("sbc_compassion.default_template").id
        template_id = safe_int(kwargs.get("template_id"), default_template_id)
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
            "template_id": template_id,
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
