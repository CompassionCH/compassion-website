from openupgradelib import openupgrade
from odoo import api, SUPERUSER_ID

muskathlon_task_sequence = {
    "task_criminal": 6,
    "task_flight_details": 3,
    "task_medical": 4,
    "task_sign_child_protection": 5,
}


@openupgrade.migrate()
def migrate(env, version):
    for task_id, task_sequence in muskathlon_task_sequence.items():
        env.ref(f"muskathlon.{task_id}").sequence = task_sequence

