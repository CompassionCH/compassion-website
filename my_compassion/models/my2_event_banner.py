##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Elias Keller <elias@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

from werkzeug.exceptions import NotFound

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request, root


class EventBanner(models.Model):
    _name = "event.banner"
    _description = "Event Banner"

    title = fields.Char(
        required=True,
        translate=True,
    )

    description = fields.Text(
        required=True,
        translate=True,
    )

    text_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("Low Black"),
    )

    start_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )

    end_date = fields.Datetime(
        required=True,
    )

    is_active = fields.Boolean(
        string="Active",
        default=True,
    )

    pictogram = fields.Many2one(
        "theme.compassion.pictograms",
        required=True,
    )

    pictogram_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("Low Blue"),
    )

    background_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("High Yellow"),
    )

    button_text = fields.Char(
        default="Learn more",
        required=True,
        translate=True,
    )

    button_text_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("Pure White"),
    )

    button_background_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("Low Blue"),
    )

    close_icon_color = fields.Many2one(
        "theme.compassion.colors",
        required=True,
        default=lambda self: self._get_default_color_by_name("Low Blue"),
    )

    button_action_url = fields.Char(
        help="URL as button action. Leave empty for no button.",
        placeholder="e.g., https://www.google.com/",
        translate=True,
    )

    target_route_ids = fields.Many2many(
        "my2.website.route",
        string="Target Pages",
        help="If pages are selected, the banner is only visible on those pages. "
             "If empty, it is visible on all pages.",
    )

    target_partner_tags = fields.Many2many(
        comodel_name="res.partner.category",
        string="Target Contact Tags",
        help="If tags are selected, the banner is only visible to users having "
             "at least one of these tags. If empty, it is visible to everyone.",
    )

    def name_get(self):
        """
        Generates the display name for the banners.
        Format: ‘Banner Title’
        """
        result = []
        for banner in self:
            result.append((banner.id, banner.title))
        return result

    @api.model
    def _get_default_color_by_name(self, color_name):
        """ """
        # Passe 'name' an, falls das Feld in 'theme.compassion.colors' anders heißt.
        color_record = self.env["theme.compassion.colors"].search(
            [("name", "=", color_name)], limit=1
        )
        return color_record.id if color_record else False

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        """Ensures that the end date is not before the start date."""
        for banner in self:
            if (
                banner.start_date
                and banner.end_date
                and banner.start_date > banner.end_date
            ):
                raise ValidationError(_("The end date must be after the start date."))

    @api.constrains("button_action_url")
    def _check_button_action_url(self):
        """Ensures that the button action URL is valid if provided."""
        allowed = {"http", "https"}
        for banner in self:
            action_url = (banner.button_action_url or "").strip()

            if not action_url:
                continue

            parsed = urlparse(action_url)
            # A URL is valid if it's a relative path (no scheme, no netloc)
            # or an absolute URL with an allowed scheme and a domain.
            is_relative = not parsed.scheme and not parsed.netloc and parsed.path

            if is_relative:
                try:
                    # Check if the relative URL corresponds to a valid route
                    routing_map = root.get_db_router(self.env.cr.dbname)
                    environ = getattr(request, "httprequest", {}).environ or {
                        "REQUEST_METHOD": "GET"
                    }
                    matcher = routing_map.bind_to_environ(environ)
                    matcher.match(action_url, method="GET")
                except NotFound as err:
                    raise ValidationError(
                        _(
                            "The relative URL '{url}' does not match any existing page."
                        ).format(url=action_url)
                    ) from err
            elif parsed.scheme in allowed and parsed.netloc:
                # It's an absolute URL, let's check if it's reachable.
                try:
                    response = requests.head(
                        action_url, timeout=5, allow_redirects=True
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    raise ValidationError(
                        _(
                            "The URL '{url}' could not be reached or is invalid. "
                            "Please check the address. (Error: {error})"
                        ).format(url=action_url, error=e)
                    ) from e
            else:
                raise ValidationError(
                    _(
                        "Invalid button action URL. "
                        "Please enter a valid relative path (e.g., /contact) "
                        "or a full URL (e.g., https://example.com)."
                    )
                )
