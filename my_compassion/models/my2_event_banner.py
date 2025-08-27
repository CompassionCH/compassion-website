# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2023 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from urllib.parse import urlparse

from urllib.parse import urlparse
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.http import request, root

class EventBanner(models.Model):
    _name = 'my_compassion.event_banner'
    _description = 'MyCompassion Event Banner'

    banner_title = fields.Char(
        required=True,
    )

    banner_description = fields.Text(
        required=True,
    )

    banner_text_color = fields.Selection(
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
        default="low-black",
        required=True,
    )


    start_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )

    end_date = fields.Datetime(
        required=True,
    )

    is_active = fields.Boolean(
        string='Active',
        default=True,
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
        required=True,
    )

    pictogram_color = fields.Selection(
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
        default="low-blue",
        required=True,
    )

    banner_background_color = fields.Selection(
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
        default="high-blue",
        required=True,
    )
    button_text = fields.Char(
        default="Learn more",
        required=True,
    )

    button_text_color = fields.Selection(
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
        default="pure-white",
        required=True,
    )

    button_background_color = fields.Selection(
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
        default="mid-yellow",
        required=True,
    )

    button_action_url = fields.Char(
        help="URL as button action. Leave empty for no button.",
        placeholder="e.g., https://www.google.com/"
    )

    target_pages = fields.Text(
        required=True
    )

    target_pages_display = fields.Html(
        compute='_compute_target_pages_display',
        sanitize=False,
        string='Target Pages'
    )


    def action_pick_routes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'my2.route.selector',
            'view_mode': 'form',
            'view_id': self.env.ref('my_compassion.view_my2_route_selector_form').id,
            'target': 'new',
            'context': {
                'default_target_model': self._name,
                'default_target_id': self.id,
                'default_target_field': 'target_pages',
            },
        }


    @api.depends('target_pages')
    def _compute_target_pages_display(self):
        for rec in self:
            parts = [p.strip() for p in (rec.target_pages or '').split(';') if p.strip()]
            if parts:
                rec.target_pages_display = (
                    '<ul class="o_route_list">'
                    + ''.join(f'<li><code>{p}</code></li>' for p in parts)
                    + '</ul>'
                )
            else:
                rec.target_pages_display = '<span class="text-muted">No pages selected</span>'


    def name_get(self):
        """
           Generates the display name for the banners.
           Format: ‘Banner Title’
        """
        result = []
        for banner in self:
            result.append((banner.id, banner.banner_title))
        return result


    #@api.model
    #def _get_controller_routes(self, public_only=True):
    #    if not request or not getattr(request, 'httprequest', None):
    #        return []
#
    #    router = root.get_db_router(self.env.cr.dbname)
    #    paths = set()
#
    #    for rule in router.iter_rules():
    #        routing = getattr(rule.endpoint, 'routing', {})
    #        if routing.get('website') and routing.get('type') == 'http':
    #            if rule.rule.startswith('/my2/'):
    #                paths.add(rule.rule)
    #    return sorted(paths)
#
    #@api.model
    #def fields_get(self, allfields=None, attributes=None):
    #    res = super().fields_get(allfields=allfields, attributes=attributes)
#
    #    """ Dynamically sets target_pages options from controller routes during HTTP requests; otherwise leaves them empty. """
    #    if res.get('target_pages', {}).get('type') == 'selection' and  request and getattr(request, 'httprequest', None):
    #        res['target_pages']['selection']  = [(p, p) for p in self._get_controller_routes()]
    #    return res

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """ Ensures that the end date is not before the start date. """
        for banner in self:
            if banner.start_date and banner.end_date and banner.start_date > banner.end_date:
                raise ValidationError("The end date must be after the start date.")

    @api.constrains('button_action_url')
    def _check_button_action_url(self):
        """ Ensures that the button action URL is valid if provided. """
        allowed = {'http', 'https'}
        for banner in self:
            action_url = (banner.button_action_url or '').strip()

            if not action_url:
               continue

            parsed = urlparse(action_url)
            if parsed.scheme not in allowed or not parsed.netloc:
                raise ValidationError("Invalid button action URL. Please enter a valid http(s) URL (e.g., https://example.com).")

