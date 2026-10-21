import json
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

STAGES = {
    "stage_all_confirmed": (
        20,
        {"fr_CH": "Confirmé", "de_DE": "Bestätigt", "it_IT": "Confermato"},
    ),
    "stage_all_staff": (28, {}),
    "stage_all_attended": (
        30,
        {"fr_CH": "Présent", "de_DE": "Teilgenommen", "it_IT": "Presente"},
    ),
    "stage_all_cancelled": (
        40,
        {"fr_CH": "Annulé", "de_DE": "Abgesagt", "it_IT": "Annullato"},
    ),
}


@openupgrade.migrate()
def migrate(env, version):
    """Order the stages shared by the event templates (T3523).

    The sequences of the database (0, 5, 7) put Confirmed before the steps of
    the journeys. Staff is only set by hand. The translations of the shared
    stages were left in English.
    """
    for xmlid, (sequence, names) in STAGES.items():
        stage = env.ref(f"website_event_compassion.{xmlid}", raise_if_not_found=False)
        if not stage:
            continue
        openupgrade.logged_query(
            env.cr,
            "UPDATE event_registration_stage "
            "SET sequence = %s, name = name || %s::jsonb WHERE id = %s",
            (sequence, json.dumps(names), stage.id),
        )
    staff = env.ref("website_event_compassion.stage_all_staff")
    staff.manual_only = True
    env["event.registration.stage"].invalidate_model(["sequence", "name"])
    _logger.info("Ordered the shared registration stages, Staff is set by hand")
