def migrate(cr, version):
    """T3377 Flag the existing trip templates and set their type of trip."""
    cr.execute(
        """
        UPDATE event_type SET is_trip = TRUE
        WHERE compassion_event_type IN ('sport', 'tour')
        """
    )
    cr.execute(
        """
        UPDATE crm_event_compassion ce
        SET trip_type = CASE WHEN ce.type = 'sport' THEN 'muskathlon'
                             ELSE 'group_trip' END
        FROM event_type et
        WHERE et.id = ce.event_type_id AND et.is_trip AND ce.trip_type IS NULL
        """
    )
