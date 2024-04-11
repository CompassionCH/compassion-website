from datetime import date

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Assume there is a similar configuration setting for 'Group Visit' events that you need to apply.
    group_visit_type = env.ref("website_event_compassion.event_type_group_visit")
    group_visits = env["crm.event.compassion"].search(
        [
            ("event_type_id", "=", group_visit_type.id),
            ("end_date", ">", date.today()),
        ]
    )
    # Replace 'your_group_visit_config' with the actual external ID of the configuration you want to apply
    group_visit_config = env.ref("module_name.your_group_visit_config")
    group_visits.write({"your_config_field": group_visit_config.id})