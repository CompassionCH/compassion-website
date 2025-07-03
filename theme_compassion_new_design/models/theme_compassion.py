from odoo import models


class ThemeCompassion(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_compassion_post_copy(self, mod):
        self.enable_view("website.template_header_default")

        self.disable_view("website.footer_custom")
        self.enable_view("website.template_footer_call_to_action")
        self.disable_view("website.option_footer_scrolltop")
