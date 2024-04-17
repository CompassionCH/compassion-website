from datetime import date

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """
    group_visit_type = env.ref("website_event_compassion.event_type_group_visit")
    group_visit = env["event.type"].search(
        [
            ("id", "=", group_visit_type.id),
        ]
    )
    group_visit_mail = env["event.type.mail"].search(
        [
            ("event_type_id", "=", group_visit_type.id),
        ]
    )
    group_visit_user = env["res.users"].search(
        [
            ("login", "=", "admin"),
        ]
    )
    group_visit_medical_survey = env["survey.survey"].search(
        [
            ("title", "=", "Medical survey"),
        ]
    )
    group_visit_feedback_survey = env["survey.survey"].search(
        [
            ("title", "=", "Feedback CSP"),
        ]
    )

    group_visit.write(
        {
            "name": "Group visit",
            "compassion_event_type": "group_visit",
            "write_uid": 1973,
            "medical_survey_id": group_visit_medical_survey.id,
            "feedback_survey_id": group_visit_feedback_survey.id,
        }
    )
    group_visit.write(
        {
            "event_type_mail_ids": [(6, 0, group_visit_mail.ids)],
        }
    )
    """