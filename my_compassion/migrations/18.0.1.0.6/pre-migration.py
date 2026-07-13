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

LOGIN_TEMPLATE_XMLIDS = [
    "register_layout",
    "login_layout",
    "override_error_message",
    "password_field",
]


def migrate(cr, version):
    """The legacy login-layout templates (a Muskathlon/Together dependency)
    now belong to my_compassion_switzerland. On databases carrying the Swiss
    module, re-home their xmlids so the orphan-data cleanup does not delete
    the views those websites render through. Everywhere else the views are
    meant to disappear with the module data.
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
          AND name = ANY(%s)
          AND model = 'ir.ui.view'
        """,
        (LOGIN_TEMPLATE_XMLIDS,),
    )
    if cr.rowcount:
        cr.execute(
            """
            UPDATE ir_ui_view
            SET key = replace(key, 'my_compassion.', 'my_compassion_switzerland.')
            WHERE key = ANY(%s)
            """,
            (["my_compassion." + name for name in LOGIN_TEMPLATE_XMLIDS],),
        )
        _logger.info(
            "Re-homed %s login templates to my_compassion_switzerland.",
            cr.rowcount,
        )
