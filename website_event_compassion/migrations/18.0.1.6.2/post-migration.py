import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """Registrations send payment links to their down payment and trip
    invoices, but online payment of invoices is a setting that is new in v18
    ('account_payment.enable_portal_payment'). Its data record is not created
    on databases migrated from v14, so every invoice showed "This invoice
    cannot be paid online." - enable it.
    """
    env["ir.config_parameter"].sudo().set_param(
        "account_payment.enable_portal_payment", True
    )
    _logger.info("T3523: enabled online payment of invoices")
