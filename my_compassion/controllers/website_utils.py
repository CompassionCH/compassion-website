##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request


def resolve_host_my2_website():
    """Return the MyCompassion website that the request host resolves to.

    Resolution is driven purely by the request host through the ormcached
    ``_get_current_website_id`` matcher, which never reads the session
    ``force_website_id``. ``get_current_website`` (and therefore
    ``request.website``) honors that sticky force, which the backend Website
    builder sets for the whole session; keying the portal landing redirects
    on the host instead keeps them from firing on backend or localhost
    requests whose session was forced onto a MyCompassion website.

    :return: the matched ``website`` record when the host is a MyCompassion
        domain, otherwise an empty ``website`` recordset.
    """
    website_model = request.env["website"].sudo()
    website_id = website_model._get_current_website_id(
        request.httprequest.host, fallback=False
    )
    website = website_model.browse(website_id)
    return website if website.is_my_compassion else website_model.browse()


def safe_int(value, default=None):
    """Return value parsed as an int, or default when it is not a valid int.

    Query string and JSON parameters reach controllers as arbitrary text or
    None. A bare int() on them turns a malformed request into a 500. This
    keeps callers in control of the fallback.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
