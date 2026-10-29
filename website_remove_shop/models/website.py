from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Website(models.Model):
    _inherit = "website"

    shop_redirect_url = fields.Char(
        help="Visitors opening the shop listing (/shop) are redirected to this"
        " page. Leave empty to answer with a 404 page.",
    )

    @api.constrains("shop_redirect_url")
    def _check_shop_redirect_url(self):
        for website in self:
            url = website.shop_redirect_url
            if not url:
                continue
            if not url.startswith("/") or url.startswith("//"):
                raise ValidationError(
                    _(
                        "The shop redirect URL must be a page of this website,"
                        " starting with a single '/'."
                    )
                )
            if url.split("?")[0].rstrip("/") == "/shop":
                raise ValidationError(
                    _("The shop redirect URL cannot be the shop itself.")
                )
