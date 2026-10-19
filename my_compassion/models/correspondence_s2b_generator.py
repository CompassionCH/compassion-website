from odoo import fields, models


class CorrespondenceS2BGenerator(models.Model):
    _inherit = "correspondence.s2b.generator"

    user_id = fields.Many2one("res.users", index=True)
    child_id = fields.Many2one("compassion.child", index=True)
    partner_id = fields.Many2one(related="user_id.partner_id", readonly=True)
    text_template_id = fields.Many2one("correspondence.prewritten.letter")

    def set_sponsorship_from_user_and_child(self):
        for generator in self:
            if generator.user_id and generator.child_id:
                partner = generator.user_id.partner_id
                sponsorship = self.env["recurring.contract"].search(
                    [
                        "|",
                        ("partner_id", "=", partner.id),
                        ("correspondent_id", "=", partner.id),
                        ("child_id", "=", generator.child_id.id),
                        ("state", "!=", "cancelled"),
                    ],
                    limit=1,
                )
                if sponsorship:
                    generator.sponsorship_ids = sponsorship
