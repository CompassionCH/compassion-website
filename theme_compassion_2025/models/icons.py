import re

from slugify import slugify

from odoo import api, fields, models


class ThemeCompassionIcons(models.Model):
    """
    This model stores the theme's SVG icons.
    """

    _name = "theme.compassion.icons"
    _inherit = "stylesheet.generator.mixin"
    _description = "MyCompassion theme icons"

    _sql_constraints = [
        (
            'class_name_unique',
            'UNIQUE(class_name)',
            'The CSS class name must be unique!'
        )
    ]

    # Fields related to the abstract stylesheet_generator_mixin class
    css_template_xml_id = (
        "theme_compassion_2025.theme_compassion_icons_stylesheet_template"
    )
    css_attachment_xml_id = "theme_compassion_2025.theme_compassion_stylesheet_icons"
    render_key = "icons"

    name = fields.Char(
        string="Name", required=True, copy=False, help="Enter the name for the icon."
    )

    class_name = fields.Char(
        string="Class Name",
        compute="_compute_class_name",
        store=True,
        readonly=True,
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
