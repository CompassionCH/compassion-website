from odoo import models


class ThemeCrowdfunding(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_crowdfunding_post_copy(self, mod):
        self.disable_view("website_theme_install.customize_modal")
