from odoo import _, api, fields, models


class CorrespondenceS2BGenerator(models.Model):
    _inherit = "correspondence.s2b.generator"

    user_id = fields.Many2one("res.users", index=True)
    child_id = fields.Many2one("compassion.child", index=True)
    partner_id = fields.Many2one(related="user_id.partner_id", readonly=True)

    @api.onchange("user_id", "child_id")
    def _onchange_user_id_child_id(self):
        """Keep sponsorship_ids in sync with the selected user and child.

        The website flow calls set_sponsorship_from_user_and_child() from its
        controller, but the backend form had no equivalent hook. Without it
        sponsorship_ids keeps whatever onchange_domain built from the default
        selection_domain, so letters were generated for an unrelated
        sponsorship whatever the user picked here.
        """
        self.set_sponsorship_from_user_and_child()
        if self.user_id and self.child_id and not self.sponsorship_ids:
            return {
                "warning": {
                    "title": _("No sponsorship found"),
                    "message": _(
                        "%(partner)s has no sponsorship for %(child)s, "
                        "so no letter can be generated for this pair.",
                        partner=self.user_id.partner_id.display_name,
                        child=self.child_id.display_name,
                    ),
                }
            }
        return None

    def set_sponsorship_from_user_and_child(self):
        for generator in self:
            if generator.user_id and generator.child_id:
                partner = generator.user_id.partner_id
                # Assigned unconditionally: keeping the previous value when the
                # search finds nothing would silently reuse the sponsorship
                # selected before the user or the child was changed.
                generator.sponsorship_ids = self.env["recurring.contract"].search(
                    [
                        "|",
                        ("partner_id", "=", partner.id),
                        ("correspondent_id", "=", partner.id),
                        ("child_id", "=", generator.child_id.id),
                        ("state", "!=", "cancelled"),
                    ],
                    limit=1,
                )
