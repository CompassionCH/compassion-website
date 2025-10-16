from odoo import fields, models, tools


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
    # The monetary value of the gift or correspondence.
    amount = fields.Char(string="Amount", readonly=True)
    # The name of the currency for the amount (e.g., USD, EUR).
    currency_name = fields.Char(string="Currency", readonly=True)
    gift_type = fields.Char(string="Gift Type", readonly=True)
    correspondence_direction = fields.Char(
        string="Correspondence Direction", readonly=True
    )

    # It is used for the date.
    create_date = fields.Char(string="Create_date", readonly=True)

    # New field for the title.
    title = fields.Char(string="Title", readonly=True)

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
                'correspondence-' || c.id AS id,
                rp.lang,
                c.child_id,
                c.partner_id,
                'correspondence' AS model,
                iat.male_singular AS title,
                c.uuid AS record_id,
                '' AS amount,
                '' AS currency_name,
                '' AS gift_type,
                c.direction AS correspondence_direction,
                TO_CHAR(c.create_date, 'DD Mon YYYY') AS create_date
            FROM correspondence c
            join res_partner rp
                on rp.id = c.partner_id
            join ir_advanced_translation iat
                on iat.lang = rp.lang
                    AND iat.src = CASE c.direction
                                  WHEN 'Beneficiary To Supporter'
                                    THEN 'Received your letter'
                                  ELSE 'Wrote you a letter'
                        END
            WHERE c.partner_id IS NOT NULL
            UNION ALL
            SELECT
                'correspondence-' || s.id AS id,
                rp.lang,
                s.child_id,
                s.partner_id,
                'sponsorship_gift' AS model,
                iat.male_singular as title,
                s.id::text AS record_id,
                s.amount::text AS amount,
                COALESCE(rc.name, 'CHF') AS currency_name,
                s.gift_type AS gift_type,
                COALESCE(s.sponsorship_gift_type, '') AS correspondence_direction,
                to_char(s.create_date, 'DD Mon YYYY') AS create_date
            FROM sponsorship_gift s
                     LEFT JOIN account_move_line aml ON aml.gift_id = s.id
                     LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            join res_partner rp
                on rp.id = s.partner_id
            join ir_advanced_translation iat
                on iat.lang = rp.lang
               and iat.src = CASE s.gift_type
                                 WHEN 'Birthday'
                                   THEN 'Sent a birthday gift'
                                 WHEN 'Graduation/Final'
                                   THEN 'Sent a graduation/final gift'
                                 WHEN 'Family Gift'
                                   THEN 'Sent a family gift'
                                 WHEN 'General'
                                   THEN 'Sent a general gift'
                                 ELSE 'Sent a gift'
                        END
            WHERE s.partner_id IS NOT NULL
                    );
            """
        )
