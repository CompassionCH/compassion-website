from odoo import api, fields, models


class My2CorrespondenceLetterTemplate(models.Model):
    """
    Represents a letter template for correspondence.
    """

    _name = "my2.correspondence.letter.template"
    _description = "My Compassion 2 Correspondence Letter Template"

    # == Fields ==
    title = fields.Char(string="Title", required=True)
    text = fields.Text(string="Text")
    start_date = fields.Date(
        string="Start Date", help="The date from which this template is valid."
    )
    end_date = fields.Date(
        string="End Date", help="The date until which this template is valid."
    )
    enabled = fields.Boolean(
        string="Enabled",
        default=False,
        copy=False,  # Avoid copying the enabled status when duplicating
        help="If checked, this template is the active one.",
    )

    status = fields.Selection(
        [("scheduled", "Scheduled"), ("active", "Active"), ("expired", "Expired")],
        string="Status",
    )

    # == ORM Overrides ==
    @api.model
    def create(self, vals):
        """
        On creation, if the new template is 'enabled', disable all other templates.
        """
        if vals.get("enabled"):
            self.search([("enabled", "=", True)]).write({"enabled": False})

        return super(My2CorrespondenceLetterTemplate, self).create(vals)

    def write(self, vals):
        """
        On update, if a template is being 'enabled', disable all other templates.
        """
        # This logic should only run if the 'enabled' field is being set to True.
        if vals.get("enabled"):
            # This finds all records but the one on creation.
            self.search([("enabled", "=", True), ("id", "not in", self.ids)]).write(
                {"enabled": False}
            )

        return super(My2CorrespondenceLetterTemplate, self).write(vals)
