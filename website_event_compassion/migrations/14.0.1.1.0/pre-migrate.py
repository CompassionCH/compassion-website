from openupgradelib import openupgrade

group_visit_data = [
    # Add tuples with the XML ID names, model names, and database IDs for "Group Visit"
    # ("xml_id_name", "model.name", database_id),
    ("group_visit_step1_email", "mail.template", 451),
    ("group_visit_step1_config", "partner.communication.config", 340),
    ("group_visit_step2_email", "mail.template",452),
    ("group_visit_step2_config", "partner.communication.config", 341),
    ("group_visit_step3_email", "mail.template",453),
    ("group_visit_step3_config", "partner.communication.config", 342),
    ("group_visit_medical_survey_email", "mail.template",454),
    ("group_visit_medical_survey_config", "partner.communication.config", 343),
    ("group_visit_medical_discharge_email", "mail.template",158),
    ("group_visit_medical_discharge_config", "partner.communication.config", 101),
    ("group_visit_travel_documents_email", "mail.template",455),
    ("group_visit_travel_documents_config", "partner.communication.config", 344),
    ("group_visit_information_day_email", "mail.template", 456),
    ("group_visit_information_day_config", "partner.communication.config", 345),
    ("group_visit_after_trip_party_email", "mail.template", 186),
    ("group_visit_after_party_config", "partner.communication.config", 110),
    ("group_visit_detailed_info_email", "mail.template", 457),
    ("group_visit_detailed_config", "partner.communication.config", 346),
    ("group_visit_before_sharing_email", "mail.template", 458),
    ("group_visit_before_sharing_config", "partner.communication.config", 347),
    ("group_visit_after_trip_feedback_email", "mail.template", 459),
    ("group_visit_after_trip_feedback_config", "partner.communication.config", 348),
]

def migrate(cr, version):
    for data in group_visit_data:
        openupgrade.add_xmlid(
            cr, "website_event_compassion", data[0], data[1], data[2], noupdate=False
        )