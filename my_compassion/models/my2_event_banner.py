# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models, fields

class EventBanner(models.Model):
    _name = 'my_compassion.event_banner'
    _description = 'MyCompassion Event Banner'

    name = fields.Char(
        string='Name',
        required=True,
        help="Internal identification for the banner."
    )
    text = fields.Html(
        string='Banner Text',
        required=True,
        help="The message to be displayed on the banner. Can contain HTML."
    )
    start_date = fields.Datetime(
        string='Start Date',
        default=fields.Datetime.now,
        help="The date and time when the banner should start being visible."
    )
    end_date = fields.Datetime(
        string='End Date',
        help="The date and time when the banner should stop being visible. "
             "Leave empty for the banner to be visible indefinitely."
    )
    target_pages = fields.Many2many(
        'website.page',
        string='Target Pages',
        help="Select the specific pages where this banner should appear. "
             "If empty, it will not appear on any page."
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Check this box to make the banner active. "
             "Uncheck to disable it without deleting it."
    )
    color = fields.Selection(
        [
            ('primary', 'Primary'),
            ('secondary', 'Secondary'),
            ('success', 'Success'),
            ('danger', 'Danger'),
            ('warning', 'Warning'),
            ('info', 'Info'),
            ('light', 'Light'),
            ('dark', 'Dark'),
        ],
        string='Color',
        default='primary',
        required=True,
        help="The background color of the banner."
    )
    button_action = fields.Char(
        string='Button Action URL',
        help="URL to redirect to when a button on the banner is clicked. "
             "Leave empty for no button."
    )
    pictogram = fields.Char(
        string='Pictogram (Font Awesome)',
        help="Enter a Font Awesome class for a pictogram, e.g., 'fa-heart'."
    )

