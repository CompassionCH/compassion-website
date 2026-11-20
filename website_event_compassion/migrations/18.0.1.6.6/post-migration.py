import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """A participant may give connection flights (T3523): more than one
    flight of each type. Odoo does not drop a removed SQL constraint."""
    env.cr.execute(
        "ALTER TABLE event_flight DROP CONSTRAINT IF EXISTS event_flight_flight_unique"
    )
    env["ir.model.constraint"].search(
        [
            ("name", "=", "event_flight_flight_unique"),
            ("model.model", "=", "event.flight"),
        ]
    ).unlink()
    _logger.info("Several flights of each type allowed per participant")
