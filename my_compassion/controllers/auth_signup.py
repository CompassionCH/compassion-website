##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from contextlib import contextmanager

from werkzeug.exceptions import BadRequest, NotFound

from odoo import _, fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.auth_signup_verify_email.controllers.main import SignupVerifyEmail


class RegistrationController(SignupVerifyEmail):
    def _signup_consent_required(self, token):
        if token:
            partner = (
                request.env["res.partner"]
                .sudo()
                ._signup_retrieve_partner(
                    token, check_validity=True, raise_exception=True
                )
            )
            return partner.signup_type == "signup" and not partner.legal_agreement_date
        return request.httprequest.path.rstrip("/").endswith("/web/signup")

    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        qcontext["signup_consent_required"] = False
        if not qcontext.get("invalid_token"):
            qcontext["signup_consent_required"] = self._signup_consent_required(
                qcontext.get("token")
            )
        return qcontext

    @contextmanager
    def _signup_consent_context(self, qcontext):
        """Validate consent and scope its server timestamp to this signup call."""
        required = self._signup_consent_required(qcontext.get("token"))
        if required and request.params.get("privacy_policy") != "accepted":
            raise UserError(
                _("Please accept the terms and conditions and the privacy policy.")
            )
        original_context = request.env.context
        key = "my_compassion_signup_consent_at"
        request.update_context(**{key: fields.Datetime.now() if required else False})
        try:
            yield
        finally:
            context = dict(request.env.context)
            context.pop(key, None)
            if key in original_context:
                context[key] = original_context[key]
            request.update_env(context=context)

    def do_signup(self, qcontext):
        with self._signup_consent_context(qcontext):
            return super().do_signup(qcontext)

    def passwordless_signup(self):
        qcontext = self.get_auth_signup_qcontext()
        if not qcontext.get("token") and not qcontext.get("signup_enabled"):
            raise NotFound()
        if request.httprequest.method != "POST" or qcontext.get("error"):
            return request.render("auth_signup.signup", qcontext)
        try:
            with self._signup_consent_context(qcontext):
                # Upstream passes request.params directly to signup. Only expose
                # identity fields and the inputs consumed by routing and CAPTCHA.
                original_params = request.params
                request.params = {
                    key: qcontext[key]
                    for key in ("login", "name", "token", "redirect")
                    if key in qcontext
                }
                if "recaptcha_token_response" in original_params:
                    request.params["recaptcha_token_response"] = original_params[
                        "recaptcha_token_response"
                    ]
                try:
                    return super().passwordless_signup()
                finally:
                    request.params = original_params
        except UserError as error:
            qcontext["error"] = error.args[0]
            return request.render("auth_signup.signup", qcontext)

    @http.route()
    def web_auth_reset_password(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        if qcontext.get("token") and not qcontext.get("invalid_token"):
            partner = (
                request.env["res.partner"]
                .sudo()
                ._signup_retrieve_partner(
                    qcontext["token"], check_validity=True, raise_exception=True
                )
            )
            if partner.signup_type == "signup":
                if request.httprequest.method == "GET":
                    query = {"token": qcontext["token"]}
                    if qcontext.get("redirect"):
                        query["redirect"] = qcontext["redirect"]
                    return request.redirect_query("/web/signup", query=query)
                raise BadRequest()
        return super().web_auth_reset_password(*args, **kw)
