from openupgradelib import openupgrade

module_data = [
    ("registration_confirmation_template", "mail.template", 347),
    ("registration_confirmation_config", "partner.communication.config", 250),
    ("sponsorship_invitation_template", "mail.template", 193),
    ("sponsorship_invitation_config", "partner.communication.config", 114),
    ("passport_and_flight_template", "mail.template", 201),
    ("passport_and_flight_config", "partner.communication.config", 121),
    ("vaccinations_template", "mail.template", 200),
    ("vaccinations_config", "partner.communication.config", 120),
    ("medical_reminder_template", "mail.template", 202),
    ("medical_reminder_config", "partner.communication.config", 122),
    ("visa_reminder_template", "mail.template", 203),
    ("visa_reminder_config", "partner.communication.config", 123),
    ("child_protection_template", "mail.template", 313),
    ("child_protection_config", "partner.communication.config", 220),
]

reload_data = [
    "security/access_rules.xml",
    "data/res_users.xml",
    "data/product.xml",
    "data/mail_template.xml",
    "data/event_type.xml",
    "data/event_registration_task.xml",
    "data/event_registration_stage.xml",
    "data/event_type_mail.xml",
    "data/website.xml",
    "templates/muskathlon_page.xml",
]

def migrate(cr, version):
    # Associate prod records to XML records
    for data in module_data:
        openupgrade.add_xmlid(
            cr, "muskathlon", data[0], data[1], data[2], noupdate=False
        )

    for data in reload_data:
        openupgrade.load_data(cr, 'muskathlon', data)