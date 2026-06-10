##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# res.partner.signup_url does not exist in v18; the URL is provided by
# partner._get_signup_url(). The account-confirmation template is noupdate,
# so its stored translations keep the dead expression unless fixed here.
_OLD = 't-attf-href="{{object.partner_id.signup_url}}"'
_NEW = 't-att-href="object.partner_id._get_signup_url()"'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref(
        "my_compassion.signup_confirmation_set_password_email",
        raise_if_not_found=False,
    )
    if not template:
        return

    cr.execute("SELECT body_html FROM mail_template WHERE id = %s", (template.id,))
    bodies = cr.fetchone()[0] or {}
    for lang, body in bodies.items():
        fixed = body.replace(_OLD, _NEW)
        if fixed != body:
            template.with_context(lang=lang).body_html = fixed
            _logger.info(
                "fixed the signup-confirmation activation link (%s)", lang
            )
