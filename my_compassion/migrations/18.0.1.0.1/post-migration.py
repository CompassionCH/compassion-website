##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Re-activate migrated views. Odoo preserves their `active=False` state on update.
# my_compassion depends on the other two, so all three must be active.
_MODULES = ["my_compassion", "theme_compassion_2025", "website_child_protection"]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    data = env["ir.model.data"].search(
        [("model", "=", "ir.ui.view"), ("module", "in", _MODULES)]
    )
    views = (
        env["ir.ui.view"]
        .with_context(active_test=False)
        .browse(data.mapped("res_id"))
        .exists()
    )

    # Theme templates use `theme.ir.ui.view`, and Odoo materializes a copy per website.
    # These materialized copies are also inactive and must be included.
    theme_data = env["ir.model.data"].search(
        [("model", "=", "theme.ir.ui.view"), ("module", "=", "theme_compassion_2025")]
    )
    views |= (
        env["ir.ui.view"]
        .with_context(active_test=False)
        .search([("theme_template_id", "in", theme_data.mapped("res_id"))])
    )

    parked = views.filtered(lambda view: not view.active)
    parked.write({"active": True})
    _logger.info("re-activated %s parked views owned by %s", len(parked), _MODULES)

    # Re-activate uncustomized, website-specific view copies (inactive copies mask the generic view).
    # Diverged copies stay archived, as their arch is outdated compared to the new parent templates.
    copies = env["ir.ui.view"].with_context(active_test=False).search(
        [
            "|",
            ("key", "like", "my_compassion.%"),
            ("key", "like", "website_child_protection.%"),
            ("website_id", "!=", False),
            ("active", "=", False),
        ]
    )
    generic_archs = {
        view.key: view.arch_db
        for view in env["ir.ui.view"].with_context(active_test=False).search(
            [("key", "in", copies.mapped("key")), ("website_id", "=", False)]
        )
    }
    synced = copies.filtered(lambda c: generic_archs.get(c.key) == c.arch_db)
    synced.write({"active": True})
    for copy in copies - synced:
        _logger.info(
            "leaving diverged website copy archived: %s (website %s)",
            copy.key,
            copy.website_id.id,
        )
    _logger.info("re-activated %s website-specific view copies", len(synced))

    # Unmask the theme's header and footer. Archived website-specific copies mask the
    # generic ones, breaking the portal layout. Re-activate them if uncustomized.
    theme = env["ir.module.module"].search([("name", "=", "theme_compassion_2025")])
    theme_websites = env["website"].search([("theme_id", "=", theme.id)])
    for key in ("website.template_header_default", "website.footer_custom"):
        generic = env["ir.ui.view"].search(
            [("key", "=", key), ("website_id", "=", False)]
        )
        masked = env["ir.ui.view"].with_context(active_test=False).search(
            [
                ("key", "=", key),
                ("website_id", "in", theme_websites.ids),
                ("active", "=", False),
            ]
        )
        unmask = masked.filtered(lambda c: c.arch_db == generic.arch_db)
        unmask.write({"active": True})
        _logger.info(
            "unmasked %s on websites %s",
            key,
            unmask.mapped("website_id.id"),
        )

    # Remove the legacy, unmanaged sponsor_id portal rule on compassion.child.
    # It is replaced by the managed child_portal rule.
    child_model = env["ir.model"]._get("compassion.child")
    portal = env.ref("base.group_portal")
    for rule in env["ir.rule"].with_context(active_test=False).search(
        [("model_id", "=", child_model.id)]
    ):
        managed = env["ir.model.data"].search_count(
            [("model", "=", "ir.rule"), ("res_id", "=", rule.id)]
        )
        if not managed and portal in rule.groups and "sponsor_id" in (rule.domain_force or ""):
            _logger.info("removing orphan compassion.child rule %r", rule.name)
            rule.unlink()
