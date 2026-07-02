import re

from slugify import slugify

from odoo import api, fields, models

PALETTE_SLOTS = {
    "o-color-1": "core-blue",
    "o-color-2": "dark-blue",
    "o-color-3": "low-eggshell",
    "o-color-4": "pure-white",
    "o-color-5": "off-black",
}


class ThemeCompassionColor(models.Model):
    """
    This model stores the theme's colors.
    """

    _name = "theme.compassion.colors"
    _inherit = "stylesheet.generator.mixin"
    _description = "MyCompassion theme colors"

    _sql_constraints = [
        (
            "class_name_unique",
            "UNIQUE(class_name)",
            "The CSS class name must be unique!",
        )
    ]

    # Fields related to the abstract stylesheet_generator_mixin class
    css_template_xml_id = (
        "theme_compassion_2025.theme_compassion_colors_stylesheet_template"
    )
    css_attachment_xml_id = "theme_compassion_2025.theme_compassion_stylesheet_colors"
    render_key = "colors"

    name = fields.Char(
        string="Name", required=True, copy=False, help="Enter the name for the color."
    )

    class_name = fields.Char(
        string="Class Name",
        compute="_compute_class_name",
        store=True,
        readonly=True,
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

    @api.model
    def _generate_stylesheet(self):
        super()._generate_stylesheet()
        colors = {color.class_name: color.color for color in self.search([])}
        palette = {slot: colors.get(name) for slot, name in PALETTE_SLOTS.items()}
        if all(palette.values()):
            self._render_to_attachment(
                "theme_compassion_2025.theme_compassion_palette_stylesheet_template",
                "theme_compassion_2025.theme_compassion_stylesheet_palette",
                {"palette": palette},
            )
