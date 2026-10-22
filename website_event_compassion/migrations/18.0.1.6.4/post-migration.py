def migrate(cr, version):
    # T3519: the communications sent after a stage were marked as done, so the
    # scheduler skipped them and the registrations reaching the stage later
    # never got them. They are tracked per registration: never done.
    cr.execute(
        """
        UPDATE event_mail SET mail_done = FALSE
        WHERE interval_type IN ('after_stage', 'after_sub')
          AND communication_id IS NOT NULL
          AND mail_done
        """
    )
