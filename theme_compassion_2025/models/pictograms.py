import base64
import re

from slugify import slugify

from odoo import api, fields, models


class ThemeCompassionPictograms(models.Model):
    """
    This model stores the theme's SVG pictograms.
    """

    _name = "theme.compassion.pictograms"
    _description = "MyCompassion theme pictograms"

    name = fields.Char(
        string="Name",
        required=True,
        copy=False,
        help="Enter the name for the pictogram.",
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
        help="Upload the pictogram's SVG file.",
    )

    @api.depends("name")
    def _compute_class_name(self):
        """
        Generates the kebab-case css class name from the name field.
        Example: 'My AwesomePictogram!' -> 'pictogram-my-awesome-pictogram'
        """
        for record in self:
            if record.name:
                # slugify handles lowercase, spaces, and special characters
                record.class_name = "pictogram-" + slugify(
                    re.sub(r"(?<!^)(?=[A-Z])", " ", record.name)
                )
            else:
                record.class_name = False

    @api.model
    def _generate_stylesheet(self):
        """
        This method generates CSS pictogram classes and updates the attachment.
        """

        # First check if the template doesn't exist yet.
        # This can happen during the initial installation/update.
        # If so, hooks._post_init_hook will call again the method
        # after the records have been added.
        template = self.env['ir.model.data'].search_read(
            [('name', '=', 'theme_compassion_pictograms_stylesheet_template'),
             ('module', '=', 'theme_compassion_2025')],
            ['res_id']
        )
        if not template:
            return

        # Search for all pictogram records
        pictograms = self.search([])

        # Render the QWeb template
        css_content = self.env["ir.qweb"]._render(
            "theme_compassion_2025.theme_compassion_pictograms_stylesheet_template",
            {"pictograms": pictograms},
        )
        css_content_b64 = base64.b64encode(css_content)

        # Find the attachment using its XML ID
        attachment = self.env.ref(
            "theme_compassion_2025.theme_compassion_stylesheet_pictograms"
        )

        # Update its content
        attachment.write({"datas": css_content_b64})

        # Force-reload web.assets_frontend
        self.env["ir.qweb"]._get_asset_nodes("web.assets_frontend", {}, js=False)

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
