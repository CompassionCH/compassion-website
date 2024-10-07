import uuid
from datetime import datetime
from random import randint

from werkzeug.exceptions import BadRequest, Gone, NotFound

from odoo import http
from odoo.http import request


class WebsiteChild(http.Controller):
    _children_per_page = 12

    @http.route(
        [
            "/children/",
            "/children/page/<int:page>",
            "/children/<string:random>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def children_page(self, page=1, random=False, **kwargs):
        website_domain = request.website.website_domain()
        child_obj = request.env["compassion.child"]
        domain = [
            ("is_published", "=", True),
            ("state", "in", child_obj._available_states()),
            ("hold_id.expiration_date", ">", datetime.now()),
            "|",
            ("website_reservation_date", "=", False),
            "&",
            ("website_reservation_id", "=", request.session.session_token),
            ("website_reservation_id", "!=", False),
        ]
        offset = (page - 1) * self._children_per_page
        domain = self._extend_search_domain(domain, kwargs)
        children = child_obj.search(
            domain + website_domain,
            offset=offset,
            limit=self._children_per_page,
            order="unsponsored_since asc, create_date asc, completion_date asc",
        )
        if not children:
            return self.load_child(**kwargs)
        if random:
            child = children[randint(0, len(children) - 1)]
            return request.redirect(
                child.website_url + "?" + request.httprequest.query_string.decode()
            )
        pager = request.website.pager(
            url=request.httprequest.path.partition("/page/")[0],
            total=children.search_count(domain + website_domain),
            page=page,
            step=self._children_per_page,
            url_args=kwargs,
        )
        field_offices = request.env["compassion.field.office"].search(
            [("available_on_childpool", "=", True)]
        )
        return request.render(
            "website_sponsorship.children_page_template",
            {"children": children, "field_offices": field_offices, "pager": pager},
        )

    def _extend_search_domain(self, domain, kwargs):
        """
        Extend the search domain with the parameters given in the URL
        @param domain: search domain of children
        @param kwargs: request parameters dict
        @return: the extended domain
        """
        if kwargs.get("age_min"):
            domain.append(("age", ">=", kwargs.get("age_min")))
        if kwargs.get("age_max"):
            domain.append(("age", "<=", kwargs.get("age_max")))
        if kwargs.get("country"):
            country = kwargs.get("country")
            # Special case for Indonesia with two field offices
            if country == "ID":
                country += ",IO"
            domain.append(("field_office_id.field_office_id", "in", country.split(",")))
        if kwargs.get("gender"):
            domain.append(("gender", "=", kwargs.get("gender")))
        if kwargs.get("birthday"):
            domain.append(("birthdate", "like", kwargs.get("birthday")[4:]))
        return domain

    def load_child(self, **kwargs):
        # Put a child on hold and display its page
        return request.render("website_sponsorship.load_child_page")

    @http.route(
        [
            # [T1835] : Note: the route MUST be specified *without* a trailing "/" otherwise when a child with a given id does not exist, the 404 Not Found page is not displayed and instead we get an infinite redirect loop. The root cause is that specifying a path with a trailing "/" adds the "/" to the path, and then ir_http.py (https://github.com/odoo/odoo/blob/f2765d2cab5671a010404c36842bf1b4c4d6350b/addons/website/models/ir_http.py#L265) redirects to a version without the "/", creating the infinite loop.
            "/child/<model('compassion.child'):child>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_page(self, child, show_sponsorship_form=False, **kwargs):
        if child.state != "N":
            raise NotFound()
        return request.render(
            "website_sponsorship.child_page_template",
            {
                "main_object": child,
                "project": child.project_id,
                "show_sponsorship_form": show_sponsorship_form,
                "sponsorship_type": kwargs.pop("sponsorship_type", "S"),
                **kwargs,
            },
        )

    @http.route(
        [
            "/child/<model('compassion.child'):child>/sponsor",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def child_sponsor_form(self, child, **kwargs):
        if child.state != "N":
            raise NotFound()
        reservation_uuid = self._get_reservation_uuid()
        if not child.sudo().reserve_for_web_sponsorship(reservation_uuid):
            raise Gone()
        return self.child_page(child, show_sponsorship_form=True, **kwargs)

    @http.route(
        [
            "/child/<string(length=11):child_ref>-<int:child_id>/"
            "sponsor/confirmation",
            "/child/<int:child_id>/sponsor/confirmation",
            "/child/<string(length=11):child_ref>-<int:child_id>/confirmation",
            "/child/<int:child_id>/confirmation",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def sponsorship_confirmation(self, child_id, **kwargs):
        contract = (
            request.env["recurring.contract"]
            .sudo()
            .search([("child_id", "=", child_id), ("state", "=", "draft")], limit=1)
        )
        if not contract:
            raise BadRequest()
        contract_partner = contract.correspondent_id
        child = contract.child_id
        main_languages = request.env["res.lang"].sudo().search([])
        spoken_languages = (
            request.env["res.lang.compassion"]
            .sudo()
            .search([("translatable", "=", True)])
        )
        payment_modes = (
            request.env["account.payment.mode"]
            .sudo()
            .search([("website_published", "=", True)])
        )
        origins = (
            request.env["recurring.contract.origin"]
            .sudo()
            .search([("website_published", "=", True)])
        )
        return request.render(
            "website_sponsorship.sponsorship_done",
            {
                "main_object": child,
                "contract": contract,
                "partner": contract_partner,
                "spoken_lang": spoken_languages,
                "main_languages": main_languages,
                "payment_modes": payment_modes,
                "origins": origins,
                "done": kwargs.get("done", not contract.is_first_sponsorship),
                "face_reveal": kwargs.get("face_reveal"),
            },
        )

    @http.route(
        ["/hold_a_child"], type="json", auth="public", sitemap=False, website=False
    )
    def hold_a_child(self):
        return (
            request.env["compassion.child"]
            .sudo()
            .website_hold_child(request.jsonrequest)
        )

    def _get_reservation_uuid(self):
        reservation_uuid = request.session.get("reservation_uuid")
        if not reservation_uuid:
            if request.env.user._is_public():
                reservation_uuid = str(uuid.uuid4())
            else:
                reservation_uuid = request.env.user.partner_id.uuid
            request.session["reservation_uuid"] = reservation_uuid
        return reservation_uuid
