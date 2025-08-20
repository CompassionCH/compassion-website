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

    pictogram = fields.Selection(
        [
            ("advocacy", "Advocacy"),
            ("bible-gift", "Bible Gift"),
            ("birthday-gift", "Birthday Gift"),
            ("buildings-city", "Buildings City"),
            ("buildings-house", "Buildings House"),
            ("buildings-neighbourhood", "Buildings Neighbourhood"),
            ("buildings-rural", "Buildings Rural"),
            ("centre-gift", "Centre Gift"),
            ("child-focused", "Child Focused"),
            ("child-sponsorship", "Child Sponsorship"),
            ("children", "Children"),
            ("christ-centred", "Christ Centred"),
            ("christmas-gift", "Christmas Gift"),
            ("church-based", "Church Based"),
            ("cognitive-brain", "Cognitive Brain"),
            ("critical-needs", "Critical Needs"),
            ("disaster-relief", "Disaster Relief"),
            ("education-and-training", "Education And Training"),
            ("family", "Family"),
            ("family-gift", "Family Gift"),
            ("food", "Food"),
            ("gift-donation-general", "Gift Donation General"),
            ("globe-global", "Globe Global"),
            ("health", "Health"),
            ("highly-vulnerable-children", "Highly Vulnerable Children"),
            ("income-generation", "Income Generation"),
            ("infrastructure", "Infrastructure"),
            ("letter-writing", "Letter Writing"),
            ("local-empowerment-partnership", "Local Empowerment Partnership"),
            ("location-pin", "Location Pin"),
            ("mothers-and-babies", "Mothers And Babies"),
            ("neighbourhood", "Neighbourhood"),
            ("physical", "Physical"),
            ("socio-emotional", "Socio Emotional"),
            ("spiritual", "Spiritual"),
            ("unsponsored-children", "Unsponsored Children"),
            ("virus", "Virus"),
            ("water-and-sanitation", "Water And Sanitation"),
            ("were-most-needed", "Were Most Needed"),
        ],
    )

    color = fields.Selection(
        [
            ("core-blue", "Core Blue"),
            ("dark-blue", "Dark Blue"),
            ("low-blue", "Low Blue"),
            ("mid-blue", "Mid Blue"),
            ("high-blue", "High Blue"),
            ("low-green", "Low Green"),
            ("mid-green", "Mid Green"),
            ("high-green", "High Green"),
            ("low-yellow", "Low Yellow"),
            ("mid-yellow", "Mid Yellow"),
            ("high-yellow", "High Yellow"),
            ("low-pink", "Low Pink"),
            ("mid-pink", "Mid Pink"),
            ("high-pink", "High Pink"),
            ("low-orange", "Low Orange"),
            ("mid-orange", "Mid Orange"),
            ("high-orange", "High Orange"),
            ("low-brown", "Low Brown"),
            ("mid-brown", "Mid Brown"),
            ("high-brown", "High Brown"),
            ("low-black", "Low Black"),
            ("off-black", "Off Black"),
            ("low-grey", "Low Grey"),
            ("mid-grey", "Mid Grey"),
            ("low-eggshell", "Low Eggshell"),
            ("mid-eggshell", "Mid Eggshell"),
            ("high-eggshell", "High Eggshell"),
            ("pure-white", "Pure White"),
        ],
        required=True,
        string="Color",
        help="The background color of the banner."
    )

    button_action = fields.Char(
        string='Button Action URL',
        help="URL to redirect to when a button on the banner is clicked. "
             "Leave empty for no button."
    )
