from odoo import models


class ThemeMuskathlon(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_muskathlon_post_copy(self, mod):
        self.enable_view("website.template_header_hamburger")
        self.enable_view("website.template_footer_links")
