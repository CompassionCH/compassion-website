##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Gergely <dgergely@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

_logger = logging.getLogger(__name__)

# partner.communication.job has no `lang` field, so `{{object.lang}}` is dead.
# Odoo 14 never evaluated the template's lang, but v18 does (_classify_per_lang),
# which makes every affected communication fail to render. The templates are
# noupdate (and one has no XML ID at all), so they can only be fixed here.


def migrate(cr, version):
    cr.execute(
        """
        UPDATE correspondence_s2b_generator
        SET partner_id = (
            SELECT partner_id FROM res_users
            WHERE res_users.id = correspondence_s2b_generator.user_id
        )
        WHERE user_id IS NOT NULL;
        """
    )
