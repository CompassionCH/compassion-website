def migrate(cr, version):
    """T3377 Turn the trip_type selection into a link to event.trip.type."""
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'crm_event_compassion' AND column_name = 'trip_type'
        """
    )
    if not cr.fetchone():
        return
    for old_value, xml_id in (
        ("group_trip", "trip_type_group"),
        ("impact_trip", "trip_type_impact"),
        ("muskathlon", "trip_type_muskathlon"),
    ):
        cr.execute(
            """
            UPDATE crm_event_compassion SET trip_type_id = d.res_id
            FROM ir_model_data d
            WHERE d.module = 'website_event_compassion' AND d.name = %s
              AND d.model = 'event.trip.type'
              AND crm_event_compassion.trip_type = %s
            """,
            (xml_id, old_value),
        )
    cr.execute("ALTER TABLE crm_event_compassion DROP COLUMN trip_type")
