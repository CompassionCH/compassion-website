##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

PORTAL_DISABLED_VIEW_KEYS = [
    "website.footer_custom",
    "website.header_search_box",
    "website.header_text_element",
    "website.header_call_to_action",
    "website_sale.template_header_default",
]

PORTAL_REMOVED_MENU_URLS = ["/", "/shop", "/jobs", "/contactus"]


class Website(models.Model):
    _inherit = "website"

    is_my_compassion = fields.Boolean(
        "MyCompassion Website",
        help="This website runs the MyCompassion sponsor portal. A"
        " multi-company instance flags one website per country.",
    )
    data_change_notification_email = fields.Char(
        "Data Change Notification Email",
        help="Recipient of partner data-change notifications from the portal."
        " Defaults to the company email when empty.",
    )
    sponsor_child_url = fields.Char(
        "Sponsor a Child URL",
        help="Target of the 'start a sponsorship' link shown to users without"
        " sponsorships. Defaults to /my2/children when empty.",
    )

    @api.model
    def get_current_website(self, fallback=True):
        # On the MyCompassion portal routes (/my2 and localized /<lang>/my2),
        # resolve to a MyCompassion website so the portal theme applies even
        # when the page is reached from another website's link or domain. The
        # domain-matched website wins when it is itself a MyCompassion site
        # (multi-company instances run one per country); anything else falls
        # back to the default MyCompassion website.
        if request:
            path_parts = [p for p in request.httprequest.path.split("/") if p]
            is_my2_route = bool(path_parts) and (
                path_parts[0] == "my2"
                or (len(path_parts) > 1 and path_parts[1] == "my2")
            )
            if is_my2_route:
                domain_website = self.browse(
                    self.sudo()._get_current_website_id(
                        request.httprequest.host, fallback=False
                    )
                )
                if domain_website and domain_website.sudo().is_my_compassion:
                    return domain_website
                target_website = self.env.ref(
                    "my_compassion.my2_website", raise_if_not_found=False
                )
                if target_website:
                    return target_website
        return super().get_current_website(fallback=fallback)

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        websites.filtered("is_my_compassion")._configure_my_compassion_portal()
        return websites

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_my_compassion"):
            self.filtered("is_my_compassion")._configure_my_compassion_portal()
        return res

    def _configure_my_compassion_portal(self):
        """Idempotently enforce the website state the portal needs, the same state a
        hand-configured instance ends up with: no stock navbar menus and no
        stock footer/header option views competing with the theme.
        """
        if not self:
            return
        view_obj = self.env["ir.ui.view"].sudo().with_context(active_test=False)
        generic_views = view_obj.search(
            [
                ("website_id", "=", False),
                "|",
                ("key", "in", PORTAL_DISABLED_VIEW_KEYS),
                ("key", "=like", "website.template_footer_%"),
            ]
        )
        for website in self:
            menus = (
                self.env["website.menu"]
                .sudo()
                .search(
                    [
                        ("website_id", "=", website.id),
                        ("url", "in", PORTAL_REMOVED_MENU_URLS),
                    ]
                )
            )
            if menus:
                _logger.info(
                    "Portal website %s: removing stock menus %s",
                    website.id,
                    menus.mapped("url"),
                )
                menus.unlink()
            specific_by_key = {
                view.key: view
                for view in view_obj.search(
                    [
                        ("key", "in", generic_views.mapped("key")),
                        ("website_id", "=", website.id),
                    ]
                )
            }
            for view in generic_views:
                specific = specific_by_key.get(view.key)
                if specific:
                    if specific.active:
                        specific.active = False
                        _logger.info(
                            "Portal website %s: archived view %s",
                            website.id,
                            view.key,
                        )
                elif view.active:
                    # Copy-on-write: creates an archived per-website copy,
                    # leaving the generic view (and other websites) untouched.
                    view.with_context(website_id=website.id).write({"active": False})
                    _logger.info(
                        "Portal website %s: disabled view %s (new archived copy)",
                        website.id,
                        view.key,
                    )
