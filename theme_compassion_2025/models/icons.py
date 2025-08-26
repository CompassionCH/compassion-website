import base64
import re

from slugify import slugify

from odoo import api, fields, models


class ThemeCompassionIcons(models.Model):
    """
    This model stores the theme's SVG icons.
    """

    _name = "theme.compassion.icons"
    _description = "MyCompassion theme icons"

    name = fields.Char(
        string="Name", required=True, copy=False, help="Enter the name for the icon."
    )

    class_name = fields.Char(
        string="Class Name",
        compute="_compute_class_name",
        store=True,
        readonly=True,
        unique=True,
        help="Auto-generated css class name in kebab-case.",
    )

    svg_file = fields.Binary(
        string="SVG File",
        required=True,
        attachment=True,
        help="Upload the icon's SVG file.",
    )

    @api.depends("name")
    def _compute_class_name(self):
        """
        Generates the kebab-case css class name from the name field.
        Example: 'My AwesomeIcon!' -> 'icon-my-awesome-icon'
        """
        for record in self:
            if record.name:
                # slugify handles lowercase, spaces, and special characters
                record.class_name = "icon-" + slugify(
                    re.sub(r"(?<!^)(?=[A-Z])", " ", record.name)
                )
            else:
                record.class_name = False

    @api.model
    def _generate_stylesheet(self):
        """
        This method generates CSS icon classes and updates the attachment.
        """
        # Search for all icon records
        icons = self.search([])

        # Render the QWeb template
        css_content = self.env["ir.qweb"]._render(
            "theme_compassion_2025.theme_compassion_icons_stylesheet_template",
            {"icons": icons},
        )
        css_content_b64 = base64.b64encode(css_content)

        # Find the attachment using its XML ID
        attachment = self.env.ref(
            "theme_compassion_2025.theme_compassion_stylesheet_icons"
        )

        # Update its content
        attachment.write({"datas": css_content_b64})

        # Force-reload web.assets_frontend
        self.env['ir.qweb']._get_asset_nodes('web.assets_frontend', {}, js=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._generate_stylesheet()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._generate_stylesheet()
        return res

    def unlink(self):
        res = super().unlink()
        self._generate_stylesheet()
        return res
