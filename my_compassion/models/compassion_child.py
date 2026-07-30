from odoo import api, fields, models


class CompassionChild(models.Model):
    _inherit = "compassion.child"

    my_sponsorship_id = fields.Many2one(
        "recurring.contract",
        compute="_compute_my_sponsorship",
        help="The sponsorship contract of the current user for this child.",
    )
    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        related="my_sponsorship_id.can_show_on_my_compassion",
    )
    can_i_write_letter = fields.Boolean(
        "Sponsor can write a letter",
        compute="_compute_can_write_letter",
        help="The current user can write a letter for this child.",
    )
    can_i_make_gift = fields.Boolean(
        "Sponsor can make a gift",
        compute="_compute_can_make_gift",
        help="The current user can make a gift for this child.",
    )

    @api.depends_context("uid")
    def _compute_my_sponsorship(self):
        partner = self.env.user.partner_id
        self.my_sponsorship_id = False  # Default value
        if not partner or not self.ids:
            return

        sponsorships = self.env["recurring.contract"].search(
            [
                ("child_id", "in", self.ids),
                "|",
                ("partner_id", "=", partner.id),
                ("correspondent_id", "=", partner.id),
            ],
            order="create_date DESC",
        )

        # Map the latest sponsorship for each child
        latest_sponsorships = {}
        for s in sponsorships:
            if s.child_id.id not in latest_sponsorships:
                latest_sponsorships[s.child_id.id] = s

        for child in self:
            child.my_sponsorship_id = latest_sponsorships.get(child.id)

    @api.depends_context("uid")
    def _compute_can_write_letter(self):
        partner = self.env.user.partner_id
        for child in self:
            sponsorship = child.my_sponsorship_id
            # Letters remain allowed while the project is suspended: they are
            # held as an "Exception" and auto-resubmitted once it reactivates
            # (see sbc_compassion correspondence.create_commkit()).
            can_write_letter = sponsorship.with_context(
                allow_during_suspension=True
            ).can_write_letter
            child.can_i_write_letter = can_write_letter and (
                partner == sponsorship.correspondent_id
                or partner.portal_sponsorships == "all_info"
            )

    @api.depends_context("uid")
    def _compute_can_make_gift(self):
        partner = self.env.user.partner_id
        for child in self:
            sponsorship = child.my_sponsorship_id
            child.can_i_make_gift = (
                sponsorship.can_make_gift and partner == sponsorship.partner_id
            )

    def get_education_status_data(self):
        """
        Returns a dictionary with education status
        """
        self.ensure_one()

        subject_count = len(self.subject_ids)
        is_enrolled = self.education_level and self.education_level != "Not Enrolled"

        return {
            "level": self.translate("education_level"),
            "is_enrolled": is_enrolled,
            "subjects_str": self.get_list("subject_ids.value"),
            "has_multiple_subjects": subject_count > 1,
            "has_subjects": subject_count > 0,
        }
