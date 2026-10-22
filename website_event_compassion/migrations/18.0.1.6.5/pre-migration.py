from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """Adopt the "Staff" stage created in the database (T3523).

    It was made by hand for the people travelling without raising funds. The
    module now ships it: give the existing stage the xmlid so that no second
    "Staff" stage is created.
    """
    # The models are not loaded yet: no env.ref() here.
    env.cr.execute(
        """
        SELECT 1 FROM ir_model_data
        WHERE module = 'website_event_compassion' AND name = 'stage_all_staff'
        """
    )
    if env.cr.fetchone():
        return
    env.cr.execute(
        """
        SELECT s.id FROM event_registration_stage s
        WHERE s.name->>'en_US' = 'Staff'
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_data d
              WHERE d.model = 'event.registration.stage' AND d.res_id = s.id
          )
        ORDER BY s.id LIMIT 1
        """
    )
    row = env.cr.fetchone()
    if row:
        openupgrade.add_xmlid(
            env.cr,
            "website_event_compassion",
            "stage_all_staff",
            "event.registration.stage",
            row[0],
            noupdate=True,
        )
