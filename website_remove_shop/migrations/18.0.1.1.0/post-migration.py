##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

_logger = logging.getLogger(__name__)

# The shop listing (/shop) is now redirected through the per-website setting
# `shop_redirect_url`. Redirects that were configured by hand in
# Website > Configuration > Redirects for /shop are replaced by that setting.
# They would not work anymore anyway: a 301/302 only applies when no route
# matches, and /shop is served by the module.


def _is_valid_target(url):
    """Same rule as Website._check_shop_redirect_url."""
    if not url or not url.startswith("/") or url.startswith("//"):
        return False
    return url.split("?")[0].rstrip("/") != "/shop"


def migrate(cr, version):
    cr.execute(
        """
        SELECT id, website_id, redirect_type, url_to, active
        FROM website_rewrite
        WHERE url_from IN ('/shop', '/shop/')
        ORDER BY id
        """
    )
    rewrites = cr.dictfetchall()
    if not rewrites:
        return

    # Active 301/302 redirects give the target. The last one wins, and a
    # redirect for a specific website wins over one for all websites.
    target_by_website = {}
    for rewrite in rewrites:
        if not rewrite["active"] or rewrite["redirect_type"] not in ("301", "302"):
            continue
        url_to = (rewrite["url_to"] or "").strip()
        if _is_valid_target(url_to):
            target_by_website[rewrite["website_id"]] = url_to
        else:
            _logger.warning(
                "Redirect %s from /shop to %r cannot be set as shop redirect:"
                " it must be a page of the website. Set it manually if needed.",
                rewrite["id"],
                url_to,
            )

    all_websites_target = target_by_website.pop(None, None)
    if all_websites_target:
        cr.execute("SELECT id FROM website")
        for (website_id,) in cr.fetchall():
            target_by_website.setdefault(website_id, all_websites_target)

    for website_id, url_to in target_by_website.items():
        cr.execute(
            """
            UPDATE website SET shop_redirect_url = %s
            WHERE id = %s AND shop_redirect_url IS NULL
            """,
            (url_to, website_id),
        )
        _logger.info("Website %s: shop redirect set to %s", website_id, url_to)

    ids = tuple(rewrite["id"] for rewrite in rewrites)
    cr.execute("DELETE FROM website_rewrite WHERE id IN %s", (ids,))
    _logger.info("Removed %s redirect(s) from /shop", len(ids))
