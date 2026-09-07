import base64

from odoo import models
from odoo.tools.misc import file_open

LOGO_PATH = "theme_muskathlon/static/src/img/compassion_4m_logo.png"


class ThemeMuskathlon(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_muskathlon_post_copy(self, mod):
        self.enable_view("website.template_header_default")
        self.enable_view("website.option_header_brand_logo")
        self.disable_view("website.option_header_brand_name")

        # Muskathlon sites are public: visitors never sign in there.
        self.disable_view("portal.user_sign_in")

        # Languages are offered by our own header flag selector only. Disabling
        # the footer parent view drops all of its variants at once.
        self.disable_view("website.header_language_selector")
        self.disable_view("portal.footer_language_selector")

        # No footer body at all, just the copyright bar.
        for footer in self._footer_templates:
            self.disable_view(footer)
        self.disable_view("website.option_footer_scrolltop")

        # New sites otherwise keep the "YOUR WEBSITE" placeholder as their logo.
        with file_open(LOGO_PATH, "rb") as logo:
            self.env["website"].get_current_website().logo = base64.b64encode(
                logo.read()
            )
