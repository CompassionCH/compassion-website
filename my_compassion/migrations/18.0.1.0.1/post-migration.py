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


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Unmask the theme's header and footer. Archived website-specific copies mask the
    # generic ones, breaking the portal layout. Re-activate them if uncustomized.
    theme = env["ir.module.module"].search([("name", "=", "theme_compassion_2025")])
    theme_websites = env["website"].search([("theme_id", "=", theme.id)])
    for key in ("website.template_header_default", "website.footer_custom"):
        generic = env["ir.ui.view"].search(
            [("key", "=", key), ("website_id", "=", False)]
        )
        masked = (
            env["ir.ui.view"]
            .with_context(active_test=False)
            .search(
                [
                    ("key", "=", key),
                    ("website_id", "in", theme_websites.ids),
                    ("active", "=", False),
                ]
            )
        )
        unmask = masked.filtered(
            lambda c, generic=generic: c.arch_db == generic.arch_db
        )
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
    for rule in (
        env["ir.rule"]
        .with_context(active_test=False)
        .search([("model_id", "=", child_model.id)])
    ):
        managed = env["ir.model.data"].search_count(
            [("model", "=", "ir.rule"), ("res_id", "=", rule.id)]
        )
        if (
            not managed
            and portal in rule.groups
            and "sponsor_id" in (rule.domain_force or "")
        ):
            _logger.info("removing orphan compassion.child rule %r", rule.name)
            rule.unlink()
