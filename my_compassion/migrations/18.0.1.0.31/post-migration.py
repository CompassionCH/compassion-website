##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.31 of my_compassion.

Magic links used the partner uuid, which public pages could leak (T3569).
Clearing the password of the accounts they created ends every session
opened with them: the session token derives from the password hash. The
donors never knew that password; they log in again with a new link or
reset their password.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE res_users SET password = NULL
        WHERE created_with_magic_link AND password IS NOT NULL
        """
    )
