from odoo import fields, models, tools, api
from odoo.tools import format_date

'''
This model is a database view that aggregates correspondence and sponsorship gifts to create a timeline
'''


class CompassionSponsorChildTimeline(models.Model):
    _name = 'compassion.sponsor_child_timeline'
    _auto = False  # important, since it's a view
    _description = 'Timeline View of the sponsor and child interactions'

    child_id = fields.Many2one('compassion.child', string="Child")
    partner_id = fields.Many2one('res.partner', string="Sponsor")
    model = fields.Char(string="Source Model")
    record_id = fields.Integer(string="Record ID")
    content = fields.Char(string="Content")
    # this field is a composite string with field data. Used for conditional rendering in the frontend
    metadata = fields.Char(string="Metadata")
    create_date = fields.Datetime(string="Created Date")
    # TODO: For both fields, handle translation in the frontend
    create_date_str = fields.Char(string="Formatted Date", compute='_compute_create_date')
    title = fields.Char(string="Title", compute='_compute_title')

    # Title mapping for sponsorship gift types (see controller for usage)
    GIFT_TITLE_MAP = {
        'Birthday': 'Birthday gift',
        'General': 'General gift',
        'Graduation/Final': 'Graduation/Final gift',
        'Family Gift': 'Family gift',
    }

    '''
    Get the title based on the model and metadata properties of the model using the GIFT_TITLE_MAP
    '''

    @api.depends('model', 'metadata')
    def _compute_title(self):
        for record in self:
            if record.model == 'correspondence':
                record.title = 'Wrote you a letter' if record.metadata == 'Beneficiary To Supporter' else 'Received your letter'
            elif record.model == 'sponsorship_gift':
                record.title = next(
                    (v for k, v in CompassionSponsorChildTimeline.GIFT_TITLE_MAP.items() if k in record.metadata),
                    'A gift')

    '''
    Format the create_date field to a human-readable string.
    '''

    @api.depends('create_date')
    def _compute_create_date(self):
        for record in self:
            record.create_date_str = record.create_date.strftime('%d %B %Y')

    '''
    Initialize the view by creating or replacing it in the database.

    In the case of sponsorship gifts, the amount is converted to text and concatenated with the currency name.
    As the currency depends on the existence of an invoice (account_move_line table), 
    we join it to get the currency name. In some cases, the currency may not be set as the invoice does not exists, 
    so we default to 'CHF'.

    init() is not __init__() because it is called by the Odoo framework when the module is installed or updated to make
    a database operation
    '''

    def init(self):
        tools.drop_view_if_exists(self._cr, 'compassion_sponsor_child_timeline')
        self._cr.execute("""
            CREATE OR REPLACE VIEW compassion_sponsor_child_timeline AS (
                SELECT
                    c.id AS id,
                    c.child_id,
                    c.partner_id,
                    'correspondence' AS model,
                    c.id AS record_id,
                    '' AS content,
                    c.direction AS metadata,
                    c.create_date
                FROM correspondence c
                WHERE c.partner_id IS NOT NULL
                UNION ALL
                SELECT
                    s.id + 1000000 AS id,  -- prevent ID clash
                    s.child_id,
                    s.partner_id,
                    'sponsorship_gift' AS model,
                    s.id AS record_id,
                    s.amount::text || ' ' || COALESCE(rc.name, 'CHF') AS content,
                    s.gift_type || '|' || COALESCE(s.sponsorship_gift_type, '') AS metadata,
                    s.create_date
                FROM sponsorship_gift s
                LEFT JOIN account_move_line aml ON aml.gift_id = s.id
                LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                WHERE s.partner_id IS NOT NULL
            );
        """)