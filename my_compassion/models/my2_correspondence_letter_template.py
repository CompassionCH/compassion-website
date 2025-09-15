from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class My2CorrespondenceLetterTemplate(models.Model):
    """
    Represents a letter template for correspondence.
    """

    _name = "my2.correspondence.letter.template"
    _description = "Correspondence Letter Template"

    # == Fields ==
    title = fields.Char(string="Title", required=True)
    text = fields.Text(string="Text")
    start_date = fields.Date(
        string="Start Date",
        help="The date from which this template is valid.",
        required=True,
    )
    end_date = fields.Date(
        string="End Date",
        help="The date until which this template is valid.",
        required=True,
    )
    scheduled = fields.Boolean(
        string="Scheduled",
        default=False,
        copy=False,
        help="If checked, this template is scheduled for use within its date range.",
    )
    status = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("expired", "Expired"),
            ("active", "Active"),
            ("disabled", "Disabled"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,  # Recommended for computed fields used in searches/filters
        help="The current status of the template    .",
    )

    @api.depends("start_date", "end_date", "scheduled")
    def _compute_status(self):
        """
        Computes the status of the template based on current date and fields.
        This logic is now exhaustive and covers all cases.
        """
        today = fields.Date.context_today(self)
        for record in self:
            is_in_date_range = (
                record.start_date
                and record.end_date
                and (record.start_date <= today <= record.end_date)
            )

            if record.end_date and record.end_date < today:
                record.status = "expired"
            elif record.scheduled:
                if is_in_date_range:
                    record.status = "active"
                elif record.start_date and record.start_date > today:
                    record.status = "scheduled"
                else:
                    record.status = "disabled"
            else:
                record.status = "disabled"

    @api.constrains("scheduled", "start_date", "end_date")
    def _check_non_overlapping_schedule(self):
        """
        Ensures that scheduled templates do not have overlapping date ranges.
        """
        for record in self:
            # Ensure start_date is before end_date
            if (
                record.start_date
                and record.end_date
                and record.start_date > record.end_date
            ):
                raise ValidationError(_("The start date must be before the end date."))

            # Only check for overlaps if the current record is scheduled
            if record.scheduled and record.start_date and record.end_date:
                # Domain to find other scheduled records that overlap
                domain = [
                    ("id", "!=", record.id),
                    ("scheduled", "=", True),
                    ("start_date", "<=", record.end_date),
                    ("end_date", ">=", record.start_date),
                ]

                conflicting_records = self.search(domain)
                if conflicting_records:
                    conflict_details = "\n".join(
                        f"{c.display_name} {c.start_date} to {c.end_date}"
                        for c in conflicting_records
                    )
                    raise ValidationError(
                        _("Conflicts with the following records:\n" + conflict_details)
                    )
