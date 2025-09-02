from odoo import _, api, fields, models, tools
from odoo.tools import format_date


class SponsorshipTimeline(models.Model):
    """Sponsorship Timeline View.

    This model is a database view that aggregates correspondence and
    sponsorship gifts to create a timeline of interactions between a sponsor
    and their sponsored child.
    """

    _name = "sponsorship.timeline"
    _auto = False  # This model is a database view, so its table is not managed by Odoo.
    _description = "Timeline View of the sponsor and child interactions"

    child_id = fields.Many2one("compassion.child", string="Child")
    partner_id = fields.Many2one("res.partner", string="Sponsor")
    model = fields.Char(string="Source Model")
    record_id = fields.Char(string="Record ID")
    content = fields.Char(string="Content")
    # This field is a composite string with data from the source record.
    # It is used for conditional rendering in the frontend.
    metadata = fields.Char(string="Metadata")
    create_date = fields.Datetime(string="Created Date")
    # TODO: For both fields, handle translation in the frontend.
    create_date_str = fields.Char(
        string="Formatted Date", compute="_compute_create_date"
    )
    title = fields.Char(string="Title", compute="_compute_title")

    # Title mapping for sponsorship gift types.
    GIFT_TITLE_MAP = {
        "Birthday": _("Birthday gift"),
        "General": _("General gift"),
        "Graduation/Final": _("Graduation/Final gift"),
        "Family Gift": _("Family gift"),
    }

    @api.depends("model", "metadata")
    def _compute_title(self):
        """Compute the title for timeline entries.

        The title is determined by the source model and its metadata.
        """
        for record in self:
            if record.model == "correspondence":
                record.title = (
                    _("Wrote you a letter")
                    if record.metadata == "Beneficiary To Supporter"
                    else _("Received your letter")
                )
            elif record.model == "sponsorship_gift":
                record.title = next(
                    (v for k, v in self.GIFT_TITLE_MAP.items() if k in record.metadata),
                    _("A gift"),
                )

    @api.depends("create_date")
    def _compute_create_date(self):
        """Format the create_date field to a human-readable string."""
        for record in self:
            record.create_date_str = format_date(
                self.env, record.create_date, date_format="d MMM yyyy"
            )

    def init(self):
        """Create or replace the database view for the timeline.

        In the case of sponsorship gifts, the amount is converted to text
        and concatenated with the currency name.
        As the currency depends on the existence of an invoice
        (account_move_line table),
        we join it to get the currency name. In some cases, the currency may not be set
        as the invoice does not exists, so we default to 'CHF'.

        Warning:
            A large integer offset (+1000000) is used for sponsorship_gift IDs
            to prevent clashes with correspondence IDs in the UNION. This is
            a common but potentially brittle technique. If the `correspondence`
            table grows beyond a million records, ID collisions will occur.
            A more robust solution would involve using a composite key.
        """
        tools.drop_view_if_exists(self._cr, "sponsorship_timeline")
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW sponsorship_timeline AS (
                SELECT
                    c.id AS id,
                    c.child_id,
                    c.partner_id,
                    'correspondence' AS model,
                    c.uuid AS record_id,
                    '' AS content,
                    c.direction AS metadata,
                    c.create_date
                FROM correspondence c
                WHERE c.partner_id IS NOT NULL
                UNION ALL
                SELECT
                s.id + 1000000 AS id,  -- Prevent ID clash with correspondence
                s.child_id,
                s.partner_id,
                'sponsorship_gift' AS model,
                 s.id::text AS record_id,
                s.amount::text || ' ' || COALESCE(rc.name, 'CHF') AS content,
                s.gift_type || '|' || COALESCE(s.sponsorship_gift_type, '') AS metadata,
                s.create_date
                FROM sponsorship_gift s
                         LEFT JOIN account_move_line aml ON aml.gift_id = s.id
                         LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                WHERE s.partner_id IS NOT NULL
                    );
            """
        )
