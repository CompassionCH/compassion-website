##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

_logger = logging.getLogger(__name__)


def ensure_recurring_instrument(tx_sudo):
    """Refuse a transaction that would leave no saved card behind.

    The my2 pages exist to set up recurring payments, so their transaction
    must either tokenize or pay with an already saved token. A crafted
    request may pick a payment method that cannot be saved: the charge
    would succeed but the monthly off-session charges would have no
    instrument. The raise rolls the transaction back, so the session
    pointer that monitor_transaction left on it is dropped too.
    """
    if tx_sudo.tokenize or tx_sudo.token_id:
        return
    _logger.warning(
        "Transaction %s on provider %s would not save a payment method."
        " Check allow_tokenization on the provider.",
        tx_sudo.reference,
        tx_sudo.provider_id.name,
    )
    request.session.pop(PaymentPostProcessing.MONITORED_TX_ID_KEY, None)
    raise ValidationError(
        _(
            "The selected payment method cannot be saved for monthly"
            " payments. Please pay by card."
        )
    )


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
