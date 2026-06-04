from odoo import api, fields, models


class Correspondence(models.Model):
    _inherit = ["website.published.mixin", "correspondence"]
    _name = "correspondence"

    is_published = fields.Boolean(
        compute="_compute_website_published",
        store=True,
    )
    website_published_manual = fields.Boolean(
        help="Prevents website publication when changed manually",
    )

    web_sort_date = fields.Datetime(
        string="Web Sort Date",
        compute="_compute_web_sort_date",
        store=True,
        index=True,
    )

    @api.depends(
        "direction",
        "state",
        "communication_state",
        "communication_type_ids",
        "sponsorship_id.state",
        "sponsorship_id.sds_state",
        "sponsorship_id.exit_communication_sent",
    )
    def _compute_website_published(self):
        for correspondence in self:
            if correspondence.website_published_manual:
                correspondence.is_published = correspondence.is_published
                continue
            if correspondence.direction == "Supporter To Beneficiary":
                correspondence.is_published = correspondence.state not in (
                    "Exception",
                    "Quality check unsuccessful",
                )
            else:
                has_valid_state = correspondence.state == "Published to Global Partner"
                if correspondence.is_final_letter:
                    # Various special checks for final letters
                    sponsorship = correspondence.sponsorship_id
                    is_exit_sent_after_letter = (
                        sponsorship.exit_communication_sent
                        and sponsorship.exit_communication_sent
                        > (correspondence.status_date or correspondence.create_date)
                    )
                    correspondence.is_published = (
                        has_valid_state
                        and sponsorship.state == "terminated"
                        and (
                            correspondence.communication_state == "done"
                            or is_exit_sent_after_letter
                        )
                    )
                else:
                    correspondence.is_published = (
                        has_valid_state and correspondence.communication_state == "done"
                    )

    def _compute_website_url(self):
        for correspondence in self:
            correspondence.website_url = correspondence.read_url

    def website_publish_button(self):
        self.website_published_manual = True
        return self.write({"is_published": not self.is_published})

    @api.depends("direction", "status_date", "create_date")
    def _compute_web_sort_date(self):
        for letter in self:
            if letter.direction == "Beneficiary To Supporter":
                letter.web_sort_date = letter.status_date or letter.create_date
            else:
                # Fallback to create_date for S->B
                letter.web_sort_date = letter.create_date
