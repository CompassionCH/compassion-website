from openupgradelib import openupgrade
from odoo import api, SUPERUSER_ID

event_registration_task_ids = [
    "task_passport",
    "task_criminal",
    "task_flight_details",
    "task_medical",
    "task_sign_child_protection",
]


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
