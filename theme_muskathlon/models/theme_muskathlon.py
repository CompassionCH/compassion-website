from odoo import models


class ThemeMuskathlon(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_muskathlon_post_copy(self, mod):
        self.enable_view("website.template_header_default")
        self.enable_view("website.option_header_brand_logo")
        self.disable_view("website.option_header_brand_name")

        # Muskathlon sites are public: visitors never sign in there.
        self.disable_view("portal.user_sign_in")

        # Languages are offered by our own flag selector only.
        self.disable_view("website.header_language_selector")
        self.disable_view("website.footer_language_selector_flag")

        # No footer body at all, just the copyright bar.
        for footer in self._footer_templates:
            self.disable_view(footer)
        self.disable_view("website.option_footer_scrolltop")
