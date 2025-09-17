import re

from slugify import slugify

from odoo import api, fields, models


class ThemeCompassionColor(models.Model):
    """
    This model stores the theme's colors.
    """

    _name = "theme.compassion.colors"
    _inherit = "stylesheet.generator.mixin"
    _description = "MyCompassion theme colors"

    # Fields related to the abstract stylesheet_generator_mixin class
    css_template_xml_id = (
        "theme_compassion_2025.theme_compassion_colors_stylesheet_template"
    )
    css_attachment_xml_id = "theme_compassion_2025.theme_compassion_stylesheet_colors"
    render_key = "colors"

    name = fields.Char(
        string="Name", required=True, copy=False, help="Enter the name for the color."
    )

    # TODO refactor uniqueness, it's not properly implemented, should use _sql_constraints
    class_name = fields.Char(
        string="Class Name",
        compute="_compute_class_name",
        store=True,
        readonly=True,
        unique=True,
        help="Auto-generated css class name in kebab-case.",
    )

    color = fields.Char(string="Color", required=True, help="Enter a valid CSS color.")

    @api.depends("name")
    def _compute_class_name(self):
        """
        Generates the kebab-case css class name from the name field.
        Example: 'Sky blue' -> 'sky-blue'
        """
        for record in self:
            if record.name:
                # slugify handles lowercase, spaces, and special characters
                record.class_name = slugify(
                    re.sub(r"(?<!^)(?=[A-Z])", " ", record.name)
                )
            else:
                record.class_name = False
