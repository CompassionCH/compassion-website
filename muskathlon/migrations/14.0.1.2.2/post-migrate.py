from openupgradelib import openupgrade

# Muskathlon registration emails link into the participant portal. The host
# was hardcoded to the donor portal (my.compassion.ch / mycompassion.ch).
# Point the path at the real route /my/events and the host at registration.host_url,

DEAD_PATH = "/my/muskathlon"
GOOD_PATH = "/my/events"
HOST_EXPR = "${registration.host_url}"
HARDCODED_HOSTS = ("https://my.compassion.ch", "https://mycompassion.ch")


def _fix_links(text):
    if not text:
        return text
    text = text.replace(DEAD_PATH, GOOD_PATH)
    for host in HARDCODED_HOSTS:
        text = text.replace(host, HOST_EXPR)
    return text


@openupgrade.migrate()
def migrate(env, version):
    templates = env["mail.template"].search([("name", "ilike", "muskathlon")])
    if not templates:
        return

    # Master
    for template in templates:
        fixed = _fix_links(template.body_html)
        if fixed != template.body_html:
            template.body_html = fixed

    # Translations
    translations = env["ir.translation"].search(
        [
            ("name", "=", "mail.template,body_html"),
            ("res_id", "in", templates.ids),
        ]
    )
    for translation in translations:
        fixed = _fix_links(translation.value)
        if fixed != translation.value:
            translation.value = fixed
