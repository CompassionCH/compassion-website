# models/route_selector.py
from odoo import api, fields, models
from odoo.http import request, root

class My2RouteSelector(models.TransientModel):
    _name = 'my2.route.selector'
    _description = 'Route Selector (wizard)'

    target_model = fields.Char(required=True, readonly=True)
    target_id    = fields.Integer(required=True, readonly=True)
    target_field = fields.Char(required=True, readonly=True)

    route_filter = fields.Char(string="Filter", default='')

    option_ids = fields.Many2many(
        'my2.route.option', 'my2_route_selector_rel',
        'selector_id', 'option_id',
        string='Routes'
    )

    def _reload_self_action(self):
        """Open/reload the same wizard record in-place (keeps modal open)."""
        self.ensure_one()
        view = self.env.ref('my_compassion.view_my2_route_selector_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': view.id,
            'target': 'new',
            'context': dict(self._context),
        }


    @api.model
    def create(self, vals):
        rec = super().create(vals)
        paths = rec._get_controller_routes()
        rec._populate_options(paths)
        rec._preselect_from_target()
        return rec


    @api.onchange('route_filter')
    def _onchange_route_filter(self):
        domain = [('selector_id', '=', self.id)]
        if self.route_filter:
            domain.append(('name', 'ilike', self.route_filter))
        return {'domain': {'option_ids': domain}}

    def _get_controller_routes(self):
        if not request or not getattr(request, 'httprequest', None):
            return []

        router = root.get_db_router(self.env.cr.dbname)
        paths = set()

        for rule in router.iter_rules():
            routing = getattr(rule.endpoint, 'routing', {})
            if routing.get('website') and routing.get('type') == 'http':
                if rule.rule.startswith('/my2/'):
                    paths.add(rule.rule)

        return sorted(paths)


    def _populate_options(self, paths=None):
        if paths is None:
            paths = []
        Opt = self.env['my2.route.option']
        if paths:
            Opt.create([{'selector_id': self.id, 'name': p, 'path': p} for p in paths])

    def _preselect_from_target(self):
        self.ensure_one()
        rec = self.env[self.target_model].browse(self.target_id).exists()
        if not rec:
            return

        raw_target_pages = getattr(rec, self.target_field, '') or ''
        selected = [p for p in raw_target_pages.split(';') if p]

        if not selected:
            return

        Option = self.env['my2.route.option']
        pick = Option.search([
            ('selector_id', '=', self.id),
            ('path', 'in', selected),
        ])
        self.option_ids = [(6, 0, pick.ids)]

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
