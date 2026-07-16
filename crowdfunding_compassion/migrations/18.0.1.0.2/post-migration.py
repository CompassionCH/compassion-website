import json
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

# "<expr> | int" is not valid QWeb/Python - it evaluates as the bitwise `|`
# operator between the expression's value and the `int` type itself, which
# raises "unsupported operand type(s) for |: 'float' and 'type'" as soon as
# the template is actually (re-)rendered. Any donation-received
# communication generated fresh (not reusing an old, already-rendered
# job) crashes on this.
_UNSAFE_PIPE_INT = {
    "invoice.amount_total | int": "int(invoice.amount_total)",
    "donation.amount_total | int": "int(donation.amount_total)",
}


def _fix_pipe_int(body):
    if not body:
        return body
    for unsafe, safe in _UNSAFE_PIPE_INT.items():
        body = body.replace(unsafe, safe)
    return body


@openupgrade.migrate()
def migrate(env, version):
    template = env.ref("crowdfunding_compassion.donation_received_email_template")
    env.cr.execute("SELECT body_html FROM mail_template WHERE id = %s", (template.id,))
    (body_html,) = env.cr.fetchone()
    if not body_html:
        return

    fixed = {lang: _fix_pipe_int(body) for lang, body in body_html.items()}
    if fixed == body_html:
        _logger.info("donation_received_email_template: nothing to fix")
        return

    env.cr.execute(
        "UPDATE mail_template SET body_html = %s WHERE id = %s",
        (json.dumps(fixed), template.id),
    )
    template.invalidate_recordset(["body_html"])
    _logger.info(
        "donation_received_email_template: fixed invalid '| int' pipe expression "
        "for languages: %s",
        ", ".join(lang for lang in fixed if fixed[lang] != body_html.get(lang)),
    )
