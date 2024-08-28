from odoo.http import Controller, request, route


class DonationController(Controller):
    @route(
        [
            "/project/<model('crowdfunding.project'):project>/donation",
            "/project/<model('crowdfunding.project'):project>/"
            "<model('crowdfunding.participant'):participant>/donation",
        ],
        auth="public",
        methods=["GET", "POST"],
        website=True,
        sitemap=False,
    )
    def project_donation_page(self, project, page=1, participant=None, **kwargs):
        """To preselect a participant, pass its id as participant query parameter"""
        if not project.website_published and not request.env.user.has_group(
            "website.group_website_designer"
        ):
            return request.redirect("/projects")
        skip_type_selection = (
            not project.number_sponsorships_goal and not project.number_csp_goal
        )
        if int(page) == 1 and len(project.participant_ids) == 1:
            page = 2
            participant = project.participant_ids
        elif int(page) == 1:
            participant = project.participant_ids[:1]
        if int(page) == 2:
            if not participant:
                page = 1
                participant = project.participant_ids[:1]
            if isinstance(participant, str):
                participant = request.env["crowdfunding.participant"].browse(
                    int(participant)
                )
            if skip_type_selection:
                # Skip directly to donation page
                page = 3

        # Used for redirection after page 2
        action_url = {
            "sponsorship": participant.sponsorship_url,
            "csp": participant.survival_sponsorship_url,
            "product": f"{project.website_url}/{participant.id}/donation?page=3",
        }
        return request.render(
            "crowdfunding_compassion.project_donation_page",
            {
                "project": project.sudo(),
                "selected_participant": participant,
                "page": page,
                "skip_type_selection": skip_type_selection,
                "participant_name": participant.nickname
                or participant.partner_id.sudo().preferred_name,
                "action_url": action_url,
            },
        )

    @route(
        "/project/<model('crowdfunding.project'):project>"
        "/<model('crowdfunding.participant'):participant>"
        "/donation/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
    )
    def post_donation_form(self, project, participant, amount, **post):
        """
        Use the cart of the website to process the donation.
        Force the price of the order line to make sure it reflects the selected
        amount for donation.
        :param project: the project record
        :param participant: the participant record
        :param amount: the donation amount
        :param post: the post request
        :return: the rendered page
        """
        if not project.is_published:
            return request.redirect("/projects")
        sale_order = request.website.sale_get_order(force_create=True).sudo()
        if sale_order.state != "draft":
            request.session["sale_order_id"] = None
            sale_order = request.website.sale_get_order(force_create=True).sudo()
        product = project.product_id
        quantity = float(amount) / product.standard_price
        price = product.standard_price
        if not quantity.is_integer():
            quantity = 1
            price = amount
        else:
            quantity = int(quantity)

        sale_order.add_donation(
            product.id,
            price,
            qty=quantity,
            participant_id=participant.id,
            opt_out=post.get("opt_out"),
            is_anonymous=post.get("is_anonymous"),
        )
        return request.redirect("/shop/checkout?express=1")

    @route(
        "/together/donation/confirmation",
        auth="public",
        website=True,
        sitemap=False,
        type="http",
    )
    def crowdfunding_donation_validate(self, **post):
        """Method called after a payment attempt"""
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            order = request.env["sale.order"].sudo().browse(sale_order_id)
            participant = order.mapped("order_line.participant_id")
            return request.render(
                "crowdfunding_compassion.donation_successful",
                {
                    "order": order,
                    "participant": participant,
                },
            )
        else:
            return request.redirect("/projects")
