from datetime import date

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute(
        """
    UPDATE account_move_line
    SET sent_to_4m = account_invoice_line.sent_to_4m
    FROM account_invoice_line
    WHERE account_move_line.old_invoice_line_id = account_invoice_line.id
    AND account_invoice_line.sent_to_4m IS NOT NULL;
    """
    )
    muskathlon_type = env.ref("muskathlon.event_type_muskathlon")
    muskathlon = env["crm.event.compassion"].search(
        [
            ("event_type_id", "=", muskathlon_type.id),
            ("end_date", ">", date.today()),
        ]
    )
    muskathlon_donation_config = env.ref(
        "muskathlon.ambassador_donation_confirmation_config"
    )
    muskathlon.write({"ambassador_config_id": muskathlon_donation_config.id})
