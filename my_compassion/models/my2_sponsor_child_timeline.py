from odoo import _, api, fields, models, tools


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

    # This field is a composite string with data from the source record.
    # It is used for conditional rendering in the frontend.
    metadata = fields.Char(string="Metadata")
    # The monetary value of the gift or correspondence.
    amount = fields.Char(string="Amount", readonly=True)
    # The name of the currency for the amount (e.g., USD, EUR).
    currency_name = fields.Char(string="Currency", readonly=True)

    # It is used for the date.
    create_date = fields.Date(string="Create Date", readonly=True)

    # New field for the title.
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

    def init(self):
        """Create or replace the database view for the timeline.

        In the case of sponsorship gifts, the amount is converted to text
        and concatenated with the currency name.
        As the currency depends on the existence of an invoice
        (account_move_line table),
        we join it to get the currency name. In some cases, the currency may not be set
        as the invoice does not exists, so we default to 'CHF'.

        """
        tools.drop_view_if_exists(self._cr, "sponsorship_timeline")
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW sponsorship_timeline AS (
              SELECT
                'correspondence-' || c.id AS id,
                c.child_id,
                c.partner_id,
                'correspondence' AS model,
                c.uuid AS record_id,
                '' AS amount,
                '' AS currency_name,
                c.direction AS metadata,
                c.create_date::date AS create_date
            FROM correspondence c
           WHERE c.partner_id IS NOT NULL
            UNION ALL
            SELECT
                'sponsorship_gift-' || s.id AS id,
                s.child_id,
                s.partner_id,
                'sponsorship_gift' AS model,
                s.id::text AS record_id,
                s.amount::text AS amount,
                COALESCE(rc.name, 'CHF') AS currency_name,
                s.gift_type || '|' || COALESCE(s.sponsorship_gift_type, '') AS metadata,
                s.create_date::date AS create_date
            FROM sponsorship_gift s
                     LEFT JOIN account_move_line aml ON aml.gift_id = s.id
                     LEFT JOIN res_currency rc ON rc.id = aml.currency_id
           WHERE s.partner_id IS NOT NULL                     
                    );
            """
        )
