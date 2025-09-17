import re

from slugify import slugify

from odoo import api, fields, models


class ThemeCompassionPictograms(models.Model):
    """
    This model stores the theme's SVG pictograms.
    """

    _name = "theme.compassion.pictograms"
    _inherit = "stylesheet.generator.mixin"
    _description = "MyCompassion theme pictograms"

    # Fields related to the abstract stylesheet_generator_mixin class
    css_template_xml_id = (
        "theme_compassion_2025.theme_compassion_pictograms_stylesheet_template"
    )
    css_attachment_xml_id = (
        "theme_compassion_2025.theme_compassion_stylesheet_pictograms"
    )
    render_key = "pictograms"

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
