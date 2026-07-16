import json
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

# T0645: the "Donation received" notification (sent to the project owner
# whenever someone donates to their TOGETHER project) already computes a
# "project" variable and even names it in some languages, but never links
# to it - even though the project's public page
# (crowdfunding.project.website_url) already exists. Anchored right before
# each language's closing signature line, since that's the only text
# guaranteed to be both present and unique in every language's current
# content.
_ANCHORS = {
    "de_DE": ("   Dein «TOGETHER»-Team von Compassion", "Projekt ansehen"),
    "en_US": ("   The Together team of Compassion Switzerland", "View your project"),
    "fr_CH": ("    L'équipe de TOGETHER de Compassion", "Voir le projet"),
    "it_IT": ("   Il team TOGETHER di Compassion Svizzera.", "Vedi il progetto"),
}


def _link_html(link_text):
    return (
        '<p><a t-attf-href="{{ object.get_base_url() }}{{ project.website_url }}">'
        f"{link_text}</a></p>\n"
    )


def _add_project_link(lang, body):
    anchor, link_text = _ANCHORS.get(lang, (None, None))
    if not anchor or anchor not in body or "project.website_url" in body:
        return body
    return body.replace(anchor, _link_html(link_text) + anchor)


@openupgrade.migrate()
def migrate(env, version):
    template = env.ref("crowdfunding_compassion.donation_received_email_template")
    env.cr.execute("SELECT body_html FROM mail_template WHERE id = %s", (template.id,))
    (body_html,) = env.cr.fetchone()
    if not body_html:
        return

    fixed = {lang: _add_project_link(lang, body) for lang, body in body_html.items()}
    if fixed == body_html:
        _logger.info("donation_received_email_template: nothing to fix")
        return

    env.cr.execute(
        "UPDATE mail_template SET body_html = %s WHERE id = %s",
        (json.dumps(fixed), template.id),
    )
    _logger.info(
        "donation_received_email_template: added project link for languages: %s",
        ", ".join(lang for lang in fixed if fixed[lang] != body_html.get(lang)),
    )
