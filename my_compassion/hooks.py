##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

_logger = logging.getLogger(__name__)


def _apply_my2_theme(env):
    """Bind theme_compassion_2025 to every MyCompassion website and run the
    theme's per-website setup, without any UI interaction.

    Idempotent: the theme binding is skipped where already set, and the theme
    setup (stylesheet generation, full page layout) can safely re-run.
    """
    websites = env["website"].search([("is_my_compassion", "=", True)])
    theme = env["ir.module.module"].search(
        [("name", "=", "theme_compassion_2025")], limit=1
    )
    if not websites or not theme:
        return
    for website in websites:
        if website.theme_id != theme:
            website.theme_id = theme
            theme.with_context(apply_new_theme=True, website_id=website.id)._theme_load(
                website
            )
            _logger.info("Applied theme %s to website %s.", theme.name, website.id)
    # The theme's own post_init hook is a no-op while no website carries the
    # theme (it targets websites by theme_id), so run it again now that the
    # bindings exist: it generates the dynamic stylesheets and sets the full
    # page layout.
    from odoo.addons.theme_compassion_2025.hooks import (
        _post_init_hook as theme_post_init,
    )

    theme_post_init(env)
    for website in websites:
        _invalidate_website_bundles(env, website)


def _invalidate_website_bundles(env, website):
    """Drop the website's cached asset bundles.

    A bundle compiled while an input could not be fetched embeds the error in
    its css and keeps the same checksum, so it is served forever unless the
    cached attachment is removed.
    """
    bundles = (
        env["ir.attachment"]
        .sudo()
        .search([("url", "like", f"/web/assets/{website.id}/%")])
    )
    if bundles:
        _logger.info(
            "Removed %s cached asset bundle(s) for website %s.",
            len(bundles),
            website.id,
        )
        bundles.unlink()


def _configure_my2_websites(env):
    """Enforce the portal website state (menus, footer/header views) on
    MyCompassion website.
    """
    env["website"].search(
        [("is_my_compassion", "=", True)]
    )._configure_my_compassion_portal()


def post_init_hook(env):
    _apply_my2_theme(env)
    _configure_my2_websites(env)
