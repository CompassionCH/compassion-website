from openupgradelib import openupgrade
from odoo import api, SUPERUSER_ID

muskathlon_task_sequence = {
    "task_criminal": 6,
    "task_flight_details": 3,
    "task_medical": 4,
    "task_sign_child_protection": 5,
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    openupgrade.set_xml_ids_noupdate_value(
        env,
        "muskathlon",
        event_registration_task_ids,
        False
    )

    env.ref('muskathlon.task_criminal').sequence = 6
    env.ref('muskathlon.task_flight_details').sequence = 3
    env.ref('muskathlon.task_medical').sequence = 4
    env.ref('muskathlon.task_sign_child_protection').sequence = 5

    openupgrade.set_xml_ids_noupdate_value(
        env,
        "muskathlon",
        event_registration_task_ids,
        True
    )
