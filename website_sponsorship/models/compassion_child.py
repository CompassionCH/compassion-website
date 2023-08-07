##############################################################################
#
#    Copyright (C) 2018-2023 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.child_compassion.models.compassion_hold import HoldType


class CompassionChild(models.Model):
    _inherit = [
        "compassion.child",
        "website.seo.metadata",
        "website.published.multi.mixin",
        "website.cover_properties.mixin"
    ]
    _name = "compassion.child"

    website_reservation_id = fields.Char()
    website_reservation_date = fields.Datetime()
    website_legend = fields.Html(compute="_compute_legend")
    website_image = fields.Char(compute="_compute_website_image")

    def _compute_website_url(self):
        super()._compute_website_url()
        for child in self:
            child.website_url = f"/child/{slug(child)}"

    def _compute_legend(self):
        legend_template = self.env.ref("website_sponsorship.child_legend")
        for child in self:
            child.website_legend = legend_template._render({"child": child})

    def _compute_website_image(self):
        image_size = self.env.context.get("image_size", "200x200")
        for child in self:
            child.website_image = request.website.image_url(
                child, "portrait", size=image_size)

    def _default_website_meta(self):
        default_meta = super()._default_website_meta()
        company = request.website.company_id.sudo()
        website_name = (request.website or company).name
        title = f"{self.preferred_name} | {website_name}"
        default_meta["default_opengraph"].update({
            "og:title": title,
            "og:image": request.website.image_url(self, "portrait"),
        })
        default_meta["default_twitter"].update({
            "twitter:title": title,
            "twitter:image": request.website.image_url(
                self, "portrait", size="300x300"),
        })
        default_meta.update({
            "default_meta_description": self._get_default_meta_description(),
        })
        return default_meta

    def _get_default_meta_description(self):
        return _(
            "Discover %s, a %s-year-old %s from %s. "
            "Become a sponsor and change %s life today. "
            "Join us in supporting %s's education, church activities, "
            "and favorite hobbies. Make a difference now!"
        ) % (
            self.preferred_name, self.age, self.get('boy'),
            self.field_office_id.country_id.name,
            self.get('his'), self.preferred_name
        )

    def website_publish_button(self):
        self.ensure_one()
        if not self.is_published and self.state not in self._available_states():
            raise UserError(_(
                "You cannot publish a child that is not available for "
                "sponsorship."))
        return super().website_publish_button()

    def reserve_for_web_sponsorship(self, session_token):
        """
        Called by website for avoiding two people requesting the same child.
        Reserve the child for 5 minutes.
        """
        self.ensure_one()
        if not self.is_available_for_web_sponsorship(session_token):
            return False
        now = fields.Datetime.now()
        self.sudo().write({
            "website_reservation_date": now,
            "website_reservation_id": session_token
        })
        delay = now + relativedelta(minutes=5)
        self.sudo().with_delay(eta=delay).write({
            "website_reservation_date": False,
            "website_reservation_id": False
        })
        return True

    def is_available_for_web_sponsorship(self, session_token):
        """
        Tells whether the child can be sponsored
        @param session_token: token of the user requesting the child
        @return: True/False
        """
        self.ensure_one()
        if self.website_reservation_date:
            return session_token and \
                self.website_reservation_id == session_token
        return True

    @api.model
    def website_hold_child(self, search_params):
        """
        Called by website JS in order to fetch a new child on the global pool
        meeting the search criteria given by the user.
        @param search_params: query parameters
        @return: id of the child record on hold
        """
        child_gender = search_params.get("gender")
        if child_gender == "M":
            child_gender = "Male"
        elif child_gender == "F":
            child_gender = "Female"
        field_office = self.env["compassion.field.office"]
        fo_code = search_params.get("country")
        if fo_code:
            # Special case for Indonesia which has two field offices
            if fo_code == "ID":
                fo_code += ",IO"
            field_office = field_office.search([(
                "field_office_id", "in", fo_code.split(","))], limit=1)
        birthday = False
        if search_params.get("birthday"):
            birthday = fields.Date.from_string(search_params.get("birthday"))
        partner = self.env.user.partner_id
        childpool = self.env["compassion.childpool.search"].create({
            "take": 1,
            "min_age": search_params.get("age_min"),
            "max_age": search_params.get("age_max"),
            "gender": child_gender,
            "field_office_ids": field_office and [(6, 0, field_office.ids)],
            "birthday_month": birthday and birthday.month,
            "birthday_day": birthday and birthday.day,
            # Make sure we find what we are looking for
            # It's not a problem to take high priority children here as
            # the chance that they will be sponsored is high and the
            # e-commerce hold shouldn't be long
            "skip": 0
        })
        childpool.do_search()
        hold_wizard = childpool.env["child.hold.wizard"].with_context(
            active_id=childpool.id, active_model=childpool._name,
            default_is_published=True,  # Directly publish the child
            async_mode=False  # Make sure we wait for the hold to be done
        ).create({
            "event_id": search_params.get("event_id"),
            "channel": "web",
            "ambassador": partner.id,
            "source_code": "website_hold_child",
            "type": HoldType.E_COMMERCE_HOLD.value,
            "expiration_date": self.env["compassion.hold"]
                .get_default_hold_expiration(HoldType.E_COMMERCE_HOLD),
            "primary_owner": 1  # Don't put the current user as owner
        })
        res = hold_wizard.send()
        child_id = res["domain"][0][2][0]
        return child_id
