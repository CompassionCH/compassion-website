import json
import logging
import pathlib

from openupgradelib import openupgrade

from odoo import Command, fields

_logger = logging.getLogger(__name__)

BODIES = pathlib.Path(__file__).parent / "bodies"

# xmlid: (sequence, registration state, names)
STAGES = {
    "stage_unconfirmed": (10, "draft", {}),
    "stage_fill_profile": (
        20,
        "open",
        {
            "en_US": "Confirmed",
            "fr_CH": "Confirmé",
            "de_DE": "Bestätigt",
            "it_IT": "Confermato",
        },
    ),
    "stage_flights": (
        21,
        None,
        {"fr_CH": "Vols", "de_DE": "Flüge", "it_IT": "Voli"},
    ),
    "stage_documents": (
        22,
        None,
        {
            "fr_CH": "Remplir les documents",
            "de_DE": "Dokumente ausfüllen",
            "it_IT": "Compilare i documenti",
        },
    ),
    "stage_criminal_record": (
        25,
        None,
        {
            "fr_CH": "Casier judiciaire",
            "de_DE": "Strafregisterauszug",
            "it_IT": "Casellario giudiziale",
        },
    ),
    "stage_ready": (
        26,
        None,
        {"fr_CH": "Prêt à partir", "de_DE": "Startklar", "it_IT": "Pronto a partire"},
    ),
}

TASK_STAGES = {
    "task_activate_account": "stage_unconfirmed",
    "task_flight_details": "stage_flights",
    "task_passport": "stage_documents",
    "task_medical": "stage_documents",
    "task_sign_child_protection": "stage_documents",
    "task_criminal": "stage_criminal_record",
}

# rule xmlid: (stage xmlid, interval unit, interval number). The registration
# confirmation stays on Confirmed: events may use their own copy of it.
STAGE_MAILS = {
    "event_mail_sponsorship": ("stage_fill_profile", "days", 15),
    "event_mail_passport_flight": ("stage_flights", "now", 1),
    "event_mail_medical": ("stage_documents", "now", 1),
    "event_mail_child_protection": ("stage_criminal_record", "now", 1),
}


def _ref(env, xmlid):
    return env.ref(f"muskathlon.{xmlid}")


def _load_texts(env):
    """The texts written for the stages, in the syntax of v18 (the v14
    conversion left Jinja in them)."""
    subjects = json.loads((BODIES / "subjects.json").read_text())
    for xmlid, subject in subjects.items():
        template = _ref(env, xmlid)
        env.cr.execute(
            "SELECT body_html, subject FROM mail_template WHERE id = %s",
            [template.id],
        )
        old_body, old_subject = env.cr.fetchone()
        body = old_body or {}
        for file in BODIES.glob(f"{xmlid}.*.html"):
            body[file.name.removeprefix(f"{xmlid}.").removesuffix(".html")] = (
                file.read_text()
            )
        openupgrade.logged_query(
            env.cr,
            "UPDATE mail_template SET body_html = %s, subject = %s WHERE id = %s",
            (
                json.dumps(body),
                json.dumps(dict(old_subject or {}, **subject)),
                template.id,
            ),
        )
    env["mail.template"].invalidate_model(["body_html", "subject"])


@openupgrade.migrate()
def migrate(env, version):
    """Give the Muskathlon the stages Unconfirmed, Confirmed, Flights, Fill
    documents, Criminal record, Ready to fly, Staff, Attended, Cancelled
    (T3523).

    - Activating the MyCompassion account confirms the registration.
    - Flights is set by hand, then each stage is left once its tasks are done.
    - The mails asking for the documents are sent when the participant
      reaches the stage of the documents, no longer some days before the
      event. The participants already past a stage don't get its mail late.
    - The texts of the mails are rewritten for their stage.

    "In Preparation" becomes the Muskathlon's "Confirmed". The participants in
    the shared "Confirmed" and in "Downpayment paid" (a stage created in the
    database without an event type) are moved there.
    """
    muskathlon = _ref(env, "event_type_muskathlon")
    for xmlid, (sequence, state, names) in STAGES.items():
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE event_registration_stage
            SET sequence = %s, registration_state = %s, name = name || %s::jsonb
            WHERE id = %s
            """,
            (sequence, state, json.dumps(names), _ref(env, xmlid).id),
        )
    env["event.registration.stage"].invalidate_model(
        ["name", "sequence", "registration_state"]
    )
    _ref(env, "stage_flights").manual_only = True
    for task, stage in TASK_STAGES.items():
        _ref(env, task).stage_id = _ref(env, stage)

    confirmed = _ref(env, "stage_fill_profile")
    env.cr.execute(
        """
        SELECT s.id FROM event_registration_stage s
        WHERE s.name->>'en_US' = 'Downpayment paid'
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_data d
              WHERE d.model = 'event.registration.stage' AND d.res_id = s.id
          )
        """
    )
    down_payment = env["event.registration.stage"].browse(
        [row[0] for row in env.cr.fetchall()]
    )
    old_stages = down_payment + env.ref("website_event_compassion.stage_all_confirmed")
    env.cr.execute(
        """
        UPDATE event_registration r SET stage_id = %s
        FROM event_event e
        WHERE e.id = r.event_id AND e.event_type_id = %s AND r.stage_id IN %s
        RETURNING r.id
        """,
        (confirmed.id, muskathlon.id, tuple(old_stages.ids)),
    )
    moved = [row[0] for row in env.cr.fetchall()]
    env["event.registration"].invalidate_model(["stage_id"])
    _logger.info("Moved Muskathlon registrations %s to Confirmed", moved)

    stages = env["event.registration.stage"]
    for xmlid in STAGES:
        stages |= _ref(env, xmlid)
    for xmlid in ("stage_all_staff", "stage_all_attended", "stage_all_cancelled"):
        stages |= env.ref(f"website_event_compassion.{xmlid}")
    muskathlon.stage_ids = [Command.set(stages.ids)]
    _logger.info("Muskathlon stages: %s", muskathlon.stage_ids.mapped("name"))

    rules = env["event.type.mail"]
    for xmlid, (stage, unit, number) in STAGE_MAILS.items():
        rule = _ref(env, xmlid)
        rule.write(
            {
                "interval_type": "after_stage",
                "stage_id": _ref(env, stage).id,
                "interval_unit": unit,
                "interval_nbr": number,
            }
        )
        rules |= rule
    _load_texts(env)
    # It used the welcome mail of the portal users, which keeps the link to
    # activate the account: the account is already active at this stage.
    _ref(env, "registration_confirmation_config").email_template_id = _ref(
        env, "registration_confirmation_template"
    )

    events = env["event.event"].search(
        [
            ("event_type_id", "=", muskathlon.id),
            ("date_end", ">=", fields.Datetime.now()),
        ]
    )
    events._sync_template_mails(rules.communication_id)
    _logger.info("Mails of the Muskathlons %s follow the stages", events.ids)

    # The group visits that went to "Downpayment paid" are put back by
    # website_switzerland, which deletes the stage once it is empty.
    down_payment.event_type_ids = [Command.clear()]
    down_payment.filtered(
        lambda stage: not env["event.registration"].search_count(
            [("stage_id", "=", stage.id)]
        )
    ).unlink()
