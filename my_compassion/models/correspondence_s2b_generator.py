from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CorrespondenceS2BGenerator(models.Model):
    _inherit = "correspondence.s2b.generator"

    generation_mode = fields.Selection(
        [
            ("single", "Single letter"),
            ("mass", "Group sending"),
        ],
        default="single",
        required=True,
        help="Group sending generates one letter per sponsorship matching the "
        "selection domain. Single letter generates one letter for an "
        "explicitly chosen user and child.",
    )
    child_id = fields.Many2one("compassion.child", index=True)
    partner_id = fields.Many2one("res.partner", index=True)

    @api.constrains("generation_mode", "child_id")
    def _check_single_mode_pair(self):
        for generator in self.filtered(lambda g: g.generation_mode == "single"):
            if not (generator.partner_id and generator.child_id):
                raise ValidationError(
                    _(
                        "A single letter needs both a user and a child. With "
                        "only one of them, the generator falls back to the "
                        "selection domain without saying so."
                    )
                )

    @api.onchange("generation_mode")
    def _onchange_generation_mode(self):
        """Never carry a selection over from the mode that was just left."""
        if self.generation_mode == "mass":
            self.child_id = False
            self.onchange_domain()
        else:
            self.sponsorship_ids = False
            self.set_sponsorship_from_user_and_child()

    @api.onchange("partner_id")
    def _onchange_partner(self):
        if self.partner_id:
            if self.child_id.partner_id != self.partner_id:
                self.child_id = False
        else:
            self.child_id = False
        return self._check_sponsor_and_child_validity()

    @api.onchange("child_id")
    def _onchange_child(self):
        """Keep sponsorship_ids in sync with the selected partner and child.

        The website flow calls set_sponsorship_from_user_and_child() from its
        controller, but the backend form had no equivalent hook. Without it
        sponsorship_ids keeps whatever onchange_domain built from the default
        selection_domain, so letters were generated for an unrelated
        sponsorship whatever the user picked here.
        """
        if self.child_id:
            self.partner_id = self.child_id.sponsor_id
            self.set_sponsorship_from_user_and_child()
        return self._check_sponsor_and_child_validity()

    def _check_sponsor_and_child_validity(self):
        if self.partner_id and self.child_id and not self.sponsorship_ids:
            return {
                "warning": {
                    "title": _("No sponsorship found"),
                    "message": _(
                        "%(partner)s has no sponsorship for %(child)s, "
                        "so no letter can be generated for this pair.",
                        partner=self.partner_id.display_name,
                        child=self.child_id.display_name,
                    ),
                }
            }
        return {}

    def set_sponsorship_from_user_and_child(self):
        for generator in self:
            if generator.partner_id and generator.child_id:
                # Assigned unconditionally: keeping the previous value when the
                # search finds nothing would silently reuse the sponsorship
                # selected before the user or the child was changed.
                generator.sponsorship_ids = self.env["recurring.contract"].search(
                    [
                        "|",
                        ("partner_id", "=", generator.partner_id.id),
                        ("correspondent_id", "=", generator.partner_id.id),
                        ("child_id", "=", generator.child_id.id),
                        ("state", "!=", "cancelled"),
                    ],
                    limit=1,
                )
