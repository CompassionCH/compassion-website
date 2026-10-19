from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class My2CorrespondencePreWrittenLetter(models.Model):
    """
    Represents a letter template for correspondence.
    """

    _name = "correspondence.prewritten.letter"
    _description = "Prewritten text for S2B Correspondence"
    _rec_name = "name"

    # == Fields ==
    name = fields.Char(required=True, translate=True)
    text = fields.Text(required=True, translate=True)
    start_date = fields.Date(
        help="The date from which this template is valid.",
        required=True,
    )
    end_date = fields.Date(
        help="The date until which this template is valid.",
        required=True,
    )
    is_active = fields.Boolean(
        string="Is active",
        default=False,
        copy=False,
        help="If checked, this template is used within its date range.",
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

    @api.depends("start_date", "end_date", "is_active")
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
            elif record.is_active:
                if is_in_date_range:
                    record.status = "active"
                elif record.start_date and record.start_date > today:
                    record.status = "scheduled"
                else:
                    record.status = "disabled"
            else:
                record.status = "disabled"

    def _unschedule_expired_templates(self):
        """
        Unschedules templates that have expired.
        This method can be called from a scheduled action.
        """
        today = fields.Date.context_today(self)
        expired_templates = self.search(
            [
                ("is_active", "=", True),
                ("end_date", "<", today),
            ]
        )
        if expired_templates:
            expired_templates.write({"is_active": False})
        return True

    @api.model
    def _cron_update_template_letter_status(self):
        """
        Updates the status of all letter templates.
        This method is called from the action with id "ir_cron_update_letter_templates".
        """
        # Unschedule expired templates
        self._unschedule_expired_templates()
        # Recompute status for all templates
        all_templates = self.search([])
        if all_templates:
            all_templates._compute_status()
        return True

    @api.constrains("is_active", "start_date", "end_date")
    def _check_non_overlapping_schedule(self):
        """
        Ensures that scheduled templates do not have overlapping date ranges.
        This also enforces that no more than one template can be active at a time.
        """
        for record in self:
            # Ensure start_date is before end_date
            if (
                record.start_date
                and record.end_date
                and record.start_date > record.end_date
            ):
                raise ValidationError(_("The start date must be before the end date."))

            # Check that the template being scheduled is not expired
            if (
                record.is_active
                and record.end_date
                and record.end_date < fields.Date.context_today(self)
            ):
                raise ValidationError(
                    _("Cannot schedule a template that is already expired.")
                )
