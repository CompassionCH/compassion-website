# models/route_selector.py
from odoo import api, fields, models
from odoo.http import request, root

class My2RouteSelector(models.TransientModel):
    _name = 'my2.route.selector'
    _description = 'Route Selector (wizard)'

    target_model = fields.Char(required=True, readonly=True)
    target_id    = fields.Integer(required=True, readonly=True)
    target_field = fields.Char(required=True, readonly=True)

    # Suchfeld (macht den View-Parse glücklich und dient als Filter)
    route_filter = fields.Char(string="Filter", default='')

    option_ids = fields.Many2many(
        'my2.route.option', 'my2_route_selector_rel',
        'selector_id', 'option_id',
        string='Routes'
    )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._populate_options()
        rec._preselect_from_target()
        return rec

    @api.onchange('route_filter')
    def _onchange_route_filter(self):
        return {'domain': {'option_ids': [('selector_id', '=', self.id),
                                          ('name', 'ilike', self.route_filter or '')]}}

    # ---- helpers ----
    def _scan_routes(self, public_only=True):
        if not request or not getattr(request, 'httprequest', None):
            return []
        router = root.get_db_router(self.env.cr.dbname)
        paths = set()
        for rule in router.iter_rules():
            routing = getattr(rule.endpoint, 'routing', {})
            if routing.get('website') and routing.get('type') == 'http':
                if '<' in rule.rule or '>' in rule.rule:
                    continue
                if rule.rule.startswith(('/web/', '/longpolling/', '/website/static/')):
                    continue
                if public_only and routing.get('auth') not in (None, 'public'):
                    continue
                paths.add(rule.rule)
        return sorted(paths)

    def _populate_options(self):
        self.ensure_one()
        Opt = self.env['my2.route.option']
        paths = self._scan_routes(public_only=True)
        if paths:
            Opt.create([{'selector_id': self.id, 'name': p, 'path': p} for p in paths])

    def _preselect_from_target(self):
        self.ensure_one()
        rec = self.env[self.target_model].browse(self.target_id).exists()
        if not rec:
            return
        wanted = {p.strip() for p in (getattr(rec, self.target_field, '') or '').split(';') if p.strip()}
        if not wanted:
            return
        pick = self.option_ids.filtered(lambda o: o.path in wanted)
        if pick:
            self.option_ids = [(6, 0, pick.ids)]

    def action_select_all_filtered(self):
        self.ensure_one()
        Opt = self.env['my2.route.option']
        to_add = Opt.search([('selector_id', '=', self.id),
                             ('name', 'ilike', self.route_filter or '')])
        self.option_ids = [(6, 0, (self.option_ids | to_add).ids)]

    def action_select_none(self):
        self.ensure_one()
        self.option_ids = [(5, 0, 0)]

    def action_apply(self):
        self.ensure_one()
        value = ';'.join(self.option_ids.mapped('path'))
        self.env[self.target_model].browse(self.target_id).write({self.target_field: value})
        return {'type': 'ir.actions.act_window_close'}


class My2RouteOption(models.TransientModel):
    _name = 'my2.route.option'
    _description = 'Route Option (transient)'

    selector_id = fields.Many2one('my2.route.selector', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    path = fields.Char(required=True)
