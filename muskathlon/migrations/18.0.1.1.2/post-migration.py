import logging

from openupgradelib import openupgrade

from odoo import Command

_logger = logging.getLogger(__name__)

# Stages created in the database for the Muskathlon without an event type
STAGE_NAMES = ("Downpayment paid",)


@openupgrade.migrate()
def migrate(env, version):
    """Link the Muskathlon stages created without an event type (T3523).

    Registrations only move to a stage without an event type when it is one
    of the stages shared by all events (Confirmed, Attended, Cancelled).
    "Downpayment paid" was created for the Muskathlon without a type: it was
    used by every event type, and would no longer be used by the Muskathlon.
    """
    muskathlon = env.ref("muskathlon.event_type_muskathlon")
    stages = (
        env["event.registration.stage"]
        .with_context(lang="en_US")
        .search([("event_type_ids", "=", False), ("name", "in", STAGE_NAMES)])
    )
    if stages:
        stages.write({"event_type_ids": [Command.link(muskathlon.id)]})
        _logger.info("Linked stages %s to the Muskathlon", stages.mapped("name"))
