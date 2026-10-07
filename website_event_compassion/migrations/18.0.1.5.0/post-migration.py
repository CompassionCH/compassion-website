import logging
import re

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# T3475: point Muskathlon mail links to the registration's website.
_HOST = (
    r"h*t+ps?:/*(?:h*t+ps?:/*)?(?:www\.)?muskathlon-[a-z]+\.ch"
    r"(?:/(?:de|en|fr|it|de_DE|en_US|fr_CH|it_IT))?"
)
_SIGNUP_RE = re.compile(
    r"\{\{\s*(?:user|partner)\.signup_url(?:\.replace\([^()]*\))?"
    r"\s*\+\s*'&(?:amp;)?redirect=/my/events'\s*\}\}"
)
_HREF_RE = re.compile(r'(?<![\w-])((?:t-attf?-)?href)="([^"]*)"')
_HREF_HOST_RE = re.compile(_HOST + r'(?=[/"{])')
_VALUE_RE = re.compile(r't-value="([^"]*)"')
_VALUE_HOST_RE = re.compile(r"(&#x27;|')" + _HOST + r"\1")
_REG_VAR_RE = re.compile(
    r'<t t-set="(\w+)" t-value="'
    r'(partner\.registration_ids\[:1\]|object\.get_objects\(\))"/>'
)
_PARTNER_SET_RE = re.compile(r'<t t-set="partner" t-value="[^"]*"/>')


def _registration_var(body):
    # get_objects() may not be a registration, so prefer an explicit binding.
    found = _REG_VAR_RE.findall(body)
    names = [name for name, _ in found]
    if "registration" in names:
        return "registration"
    bound = [name for name, value in found if value.startswith("partner.")]
    return (bound or names or [None])[0]


def _fix_href(match, var):
    attribute, url = match.groups()
    url = _HREF_HOST_RE.sub("{{" + var + ".host_url}}", url)
    # Only t-attf-href interpolates {{ }}.
    if "{{" in url and attribute == "href":
        attribute = "t-attf-href"
    return f'{attribute}="{url}"'


def _fix_body(body):
    var = _registration_var(body) or "registration"
    fixed = _SIGNUP_RE.sub("{{" + var + ".portal_signup_url}}", body)
    fixed = _HREF_RE.sub(lambda m: _fix_href(m, var), fixed)
    fixed = _VALUE_RE.sub(
        lambda m: 't-value="{}"'.format(
            _VALUE_HOST_RE.sub(f"{var}.host_url", m.group(1))
        ),
        fixed,
    )
    if fixed == body:
        return body
    # Declare the registration in bodies that did not use it yet.
    if not _registration_var(fixed):
        fixed, anchored = _PARTNER_SET_RE.subn(
            lambda m: m.group(0)
            + '<t t-set="registration" t-value="partner.registration_ids[:1]"/>',
            fixed,
            count=1,
        )
        if not anchored:
            _logger.warning("T3475: no partner variable to anchor a registration on")
            return body
    return fixed


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        "SELECT id, name, body_html FROM mail_template "
        "WHERE name::text ILIKE '%%muskathlon%%' AND ("
        "  body_html::text ~ 'muskathlon[a-z-]*\\.ch'"
        "  OR body_html::text LIKE '%%redirect=/my/events%%') ORDER BY id"
    )
    for template_id, name, bodies in cr.fetchall():
        template = env["mail.template"].browse(template_id)
        for lang, body in (bodies or {}).items():
            fixed = _fix_body(body)
            if fixed != body:
                template.with_context(lang=lang).body_html = fixed
                _logger.info(
                    "T3475: rebuilt the event links of template %s %s [%s]",
                    template_id,
                    name.get("en_US"),
                    lang,
                )
