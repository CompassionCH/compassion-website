import logging

from odoo import _
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class HomepageController(Controller):
    @route("/homepage", auth="public", website=True, sitemap=False)
    def homepage(self, **kwargs):
        return request.render(
            "crowdfunding_compassion.homepage_template",
            self._compute_homepage_context(),
        )

    def _compute_homepage_context(self):
        # Retrieve all projects open (deadline in the future)
        active_projects = (
            request.env["crowdfunding.project"]
            .sudo()
            .get_active_projects(status="active")
        )
        funds_data = []

        for fund in (
            request.env["product.product"]
            .sudo()
            .search([("activate_for_crowdfunding", "=", True)])
        ):
            funds_data.append(
                {
                    "name": fund.crowdfunding_impact_text_active,
                    "description": fund.crowdfunding_description,
                    "icon_image": fund.image_512 or active_projects.get_sponsor_icon(),
                    # the header is a small image so we can compress it to save space
                    "header_image": fund.image_400
                    if fund.image_large
                    else active_projects.get_sponsor_card_header_image(),
                }
            )

        # populate the fund information depending on the impact type and the number
        # of impact
        impact = {"sponsorship": active_projects.sponsorship_card_content()}
        for fund in (
            request.env["product.product"]
            .sudo()
            .search(
                [("product_tmpl_id.show_fund_together_homepage", "=", True)],
                order="total_fund_impact DESC",
            )
        ):
            impact_val = fund.product_tmpl_id.total_fund_impact
            if impact_val > 1:
                fund_text = fund.crowdfunding_impact_text_passive_plural
            else:
                fund_text = fund.crowdfunding_impact_text_passive_singular
            impact[fund.name] = {
                "type": "fund",
                "value": active_projects.fund_impact_val_formatting(impact_val),
                "text": fund_text,
                "description": fund.crowdfunding_description,
                "icon_image": fund.image_512 or active_projects.get_sponsor_icon(),
            }

        subheading = _("What we achieved so far")
        return {
            "projects": active_projects[:8],
            "impact": {k: v for k, v in impact.items() if v["value"]},
            "funds_description": funds_data,
            "base_url": request.website.domain,
            "subheading": subheading,
        }
