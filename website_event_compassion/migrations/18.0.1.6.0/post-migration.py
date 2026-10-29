def migrate(cr, version):
    # T3516: communications after subscription were sent once to the whole
    # event, then marked as done, so later registrations never got them. They
    # are now tracked per registration: consider the existing registrations as
    # notified so that they don't receive the communication again.
    cr.execute(
        """
        INSERT INTO event_mail_registration
            (scheduler_id, registration_id, scheduled_date, mail_sent,
             create_uid, write_uid, create_date, write_date)
        SELECT m.id, r.id, r.create_date, TRUE, 1, 1, now(), now()
        FROM event_mail m
        JOIN event_registration r ON r.event_id = m.event_id
        WHERE m.interval_type = 'after_sub'
          AND m.communication_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM event_mail_registration mr
              WHERE mr.scheduler_id = m.id AND mr.registration_id = r.id
          )
        """
    )
    cr.execute(
        """
        UPDATE event_mail SET mail_done = FALSE
        WHERE interval_type = 'after_sub' AND communication_id IS NOT NULL
        """
    )
