##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models


class EventType(models.Model):
    # Inherit from 'mail.thread' so that the followers can be notified when
    # events of the type have changed.
    _inherit = ["event.type", "mail.thread"]
    _name = "event.type"
