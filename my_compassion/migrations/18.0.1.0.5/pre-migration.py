##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """The volunteering dashboard vignette now belongs to
    my_compassion_switzerland. On databases carrying the Swiss module, re-home
    the view's xmlid before this update ends, so the orphan-data cleanup does
    not delete the view (and cascade-delete the Swiss inherit hanging on it).
    Everywhere else the view is meant to disappear with the module data.
    """
    cr.execute(
        """
        SELECT 1 FROM ir_module_module
        WHERE name = 'my_compassion_switzerland'
          AND state IN ('installed', 'to upgrade', 'to install')
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = 'my_compassion_switzerland'
        WHERE module = 'my_compassion'
          AND name = 'dashboard_volunteering_vignette'
          AND model = 'ir.ui.view'
        """
    )
    if cr.rowcount:
        cr.execute(
            """
            UPDATE ir_ui_view
            SET key = 'my_compassion_switzerland.dashboard_volunteering_vignette'
            WHERE key = 'my_compassion.dashboard_volunteering_vignette'
            """
        )
        _logger.info(
            "Re-homed the volunteering vignette view to my_compassion_switzerland."
        )
