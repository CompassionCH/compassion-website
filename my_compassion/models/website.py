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
    my2_min_donation_amount = fields.Float(
        "Minimum Donation to a Fund",
        default=5.0,
        help="Smallest amount, in the currency of the website's company, a donor"
        " may give to a fund. Card testers try stolen cards with tiny payments"
        " on public donation pages.",
    )
    my2_max_payment_attempts_per_ip = fields.Integer(
        "Visitor Payment Attempts per IP",
        default=10,
        help="Payments visitors may start on this website from one IP address"
        " within the window below, all carts and sessions together; 0 for no"
        " limit. Card testers try stolen cards one after the other on public"
        " donation pages.",
    )
    my2_payment_attempts_window = fields.Integer(
        "Visitor Payment Attempts Window (minutes)",
        default=60,
        help="The window of the visitor payment attempts per IP address.",
    )

    def sale_get_order(self, force_create=False):
        """Each cart stays on its website. The websites of a domain share the
        session (and /my2 resolves to MyCompassion on any domain), so its
        cart may come from another website:

        - on a MyCompassion website, only a draft cart of this website (and
          its company) is the cart; a cart set aside by another website
          (my2_sale_order_id) comes back when the session holds none;
        - another website never takes a MyCompassion cart: it sets it aside
          under its own session key - out of reach of website_sale, which
          reads sale_order_id directly (e.g. to merge an abandoned cart) -
          and starts its own cart if asked to.
        """
        if request:
            session = request.session
            order = (
                self.env["sale.order"]
                .sudo()
                .browse(session.get("sale_order_id"))
                .exists()
            )
            if self.is_my_compassion:
                if order and not self._my2_is_own_cart(order):
                    session.pop("sale_order_id", None)
                    session.pop("website_sale_cart_quantity", None)
                    order = order.browse()
                set_aside = (
                    self.env["sale.order"]
                    .sudo()
                    .browse(session.pop("my2_sale_order_id", None))
                    .exists()
                )
                if not order and set_aside and self._my2_is_own_cart(set_aside):
                    session["sale_order_id"] = set_aside.id
                    session["website_sale_cart_quantity"] = set_aside.cart_quantity
            elif order.website_id.is_my_compassion:
                session["my2_sale_order_id"] = session.pop("sale_order_id")
                session.pop("website_sale_cart_quantity", None)
        return super().sale_get_order(force_create=force_create)

    def _my2_is_own_cart(self, order):
        """Whether order is a draft cart of this website and its company."""
        return (
            order.website_id == self
            and order.company_id == self.company_id
            and order.state == "draft"
        )

    def _my2_offers_payment_method(self, code):
        """Whether a published payment provider of the website's company offers
        the payment method ``code`` (e.g. "blik"): its logo is then shown
        under the Pay button."""
        self.ensure_one()
        return bool(
            self.env["payment.provider"]
            .sudo()
            .search_count(
                [
                    ("company_id", "=", self.company_id.id),
                    ("state", "in", ("enabled", "test")),
                    ("is_published", "=", True),
                    ("payment_method_ids.code", "=", code),
                ],
                limit=1,
            )
        )

    def _my2_donation_products(self, domain=None, order=None):
        """The donation products (funds and gifts) the website's company
        publishes, in sudo.

        Their activation, suggested amounts and currency are per company, read
        in env.company: that is the donor's own company when the website's
        company is not one of theirs (website's _frontend_pre_dispatch). Read
        in the website's company instead, the company of the cart; sudo, as
        such a donor may not read in it, so the domain is the gate: activated
        in the website's company, and shared, of that company or of a parent
        company, as the product multi-company rule (which sudo skips) allows.
        """
        self.ensure_one()
        return (
            self.env["product.template"]
            .sudo()
            .with_company(self.company_id)
            .search(
                [
                    ("activate_for_my_compassion", "=", True),
                    *self.env["product.template"]._check_company_domain(
                        self.company_id
                    ),
                    *(domain or []),
                ],
                order=order,
            )
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
