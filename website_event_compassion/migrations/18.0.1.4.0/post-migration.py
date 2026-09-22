def migrate(cr, version):
    """T3377 Flag the existing trip templates and classify their events."""
    cr.execute(
        """
        UPDATE event_type SET is_trip = TRUE
        WHERE compassion_event_type IN ('sport', 'tour')
        """
    )
    cr.execute(
        """
        UPDATE crm_event_compassion ce
        SET trip_type_id = d.res_id
        FROM event_type et, ir_model_data d
        WHERE et.id = ce.event_type_id AND et.is_trip
          AND ce.trip_type_id IS NULL
          AND d.module = 'website_event_compassion'
          AND d.model = 'event.trip.type'
          AND d.name = CASE WHEN ce.type = 'sport' THEN 'trip_type_muskathlon'
                            ELSE 'trip_type_group' END
        """
    )
