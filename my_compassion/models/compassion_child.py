##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.child_compassion.models.compassion_hold import HoldType
from odoo.addons.sponsorship_compassion.models.contracts import SPONSORSHIP_TYPE_LIST

_logger = logging.getLogger(__name__)


class ChildNotFound(UserError):
    pass


# Portal-only French phrasing for the "I'm in <level>" sentence, keyed by
# the education_level selection's internal value. Not applied to the shared
# education_level translation itself (also shown as a plain backend field),
# where a baked-in preposition would look out of place.
PORTAL_EDUCATION_LEVEL_FR = {
    "Preschool": "à l'école enfantine",
    "Primary": "à l'école primaire",
    "Secondary": "à l'école secondaire",
    "Highschool": "au lycée",
    "University Graduate": "à l'université",
}

# Portal-only French phrasing for the "I love <hobbies>" sentence, keyed by
# the hobby's canonical English value. Only the noun-style hobbies need an
# article here ("j'aime LA musique") - verb-phrase hobbies ("danser",
# "nager") are already correct without one and are left to fall back to the
# normal translation. Not applied to the shared child.hobby translation
# itself (also shown as a plain backend tag), where an article would look
# out of place.
PORTAL_HOBBY_LABELS_FR = {
    "Ball Games": "les jeux de balle",
    "Throwing a ball": "lancer une balle",
    "Baseball": "le baseball",
    "Art or drawing": "le bricolage et dessin",
    "Story telling": "le conte",
    "Group games": "les jeux collectifs",
    "Jacks": "les cartes",
    "Cricket": "le cricket",
    "Reading": "la lecture",
    "Marbles": "les billes",
    "Music": "la musique",
    "Basketball": "le basketball",
    "Jump rope": "la corde à sauter",
    "Sports": "les sports",
    "Ping pong": "le ping-pong",
    "Hide and seek": "le cache-cache",
    "Volleyball or handball": "le volleyball ou le handball",
}


class CompassionChild(models.Model):
    _inherit = ["compassion.child", "website.published.multi.mixin"]
    _name = "compassion.child"

    my_sponsorship_id = fields.Many2one(
        "recurring.contract",
        compute="_compute_my_sponsorship",
        help="The sponsorship contract of the current user for this child.",
    )
    portal_sponsorship_ids = fields.One2many(
        "recurring.contract",
        "child_id",
        domain=[("type", "in", SPONSORSHIP_TYPE_LIST), ("state", "!=", "cancelled")],
    )
    can_show_on_my_compassion = fields.Boolean(
        string="Can be shown on My Compassion",
        compute="_compute_can_show_on_my_compassion",
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
    website_reservation_id = fields.Char()
    website_reservation_date = fields.Datetime()
    sponsorship_url = fields.Char(compute="_compute_sponsorship_url")

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
    def _compute_can_show_on_my_compassion(self):
        for child in self:
            child.can_show_on_my_compassion = (
                child.my_sponsorship_id.can_show_on_my_compassion
            )

    @api.depends_context("uid")
    def _compute_can_write_letter(self):
        partner = self.env.user.partner_id
        for child in self:
            sponsorship = child.my_sponsorship_id
            child.can_i_write_letter = sponsorship.can_write_letter_grace and (
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

    def _compute_website_url(self):
        for child in self:
            base_url = child.get_base_url().rstrip("/")
            child.website_url = f"{base_url}/my2/children/{child.id}"

    def _compute_sponsorship_url(self):
        for child in self:
            base_url = child.get_base_url().rstrip("/")
            child.sponsorship_url = f"{base_url}/my2/new-sponsorship/{child.id}"

    def get_education_status_data(self):
        """
        Returns a dictionary with education status
        """
        self.ensure_one()

        subject_count = len(self.subject_ids)
        is_enrolled = self.education_level and self.education_level != "Not Enrolled"

        level = self.translate("education_level")
        if self.env.lang == "fr_CH":
            level = PORTAL_EDUCATION_LEVEL_FR.get(self.education_level, level)

        return {
            "level": level.lower(),
            "is_enrolled": is_enrolled,
            "subjects_str": self.get_list("subject_ids.value").lower(),
            "has_multiple_subjects": subject_count > 1,
            "has_subjects": subject_count > 0,
        }

    def get_portal_hobbies_list(self):
        """
        Hobby list for the portal "I love ..." sentence. Overrides the
        shared child.hobby translation with a French phrasing that includes
        the article for noun-style hobbies (which the shared translation
        can't have, since it's also used for the admin hobby tags where an
        article would look out of place).
        """
        self.ensure_one()
        hobbies = self.hobby_ids
        if self.env.lang != "fr_CH":
            return self.get_list("hobby_ids.value")

        en_values = hobbies.with_context(lang="en_US").mapped("value")
        translated_values = hobbies.mapped("value")
        values = []
        for en_value, translated_value in zip(
            en_values, translated_values, strict=False
        ):
            value = PORTAL_HOBBY_LABELS_FR.get(en_value, translated_value)
            if value and value not in values:
                values.append(value)

        if len(values) > 1:
            return ", ".join(values[:-1]) + " " + _("and") + " " + values[-1]
        return values[0] if values else ""

    def website_publish_button(self):
        self.ensure_one()
        if not self.is_published and self.state not in self._available_states():
            raise UserError(
                _(
                    "You cannot publish a child that is not available for "
                    "sponsorship."
                )
            )
        return super().website_publish_button()

    def reserve_for_web_sponsorship(self, reservation_uuid):
        """
        Called by website for avoiding two people requesting the same child.
        Reserve the child for 5 minutes.
        """
        self.ensure_one()
        if not self.is_available_for_web_sponsorship(reservation_uuid):
            return False
        now = fields.Datetime.now()
        self.write(
            {
                "website_reservation_date": now,
                "website_reservation_id": reservation_uuid,
            }
        )
        delay = now + relativedelta(minutes=5)
        self.with_delay_sh(
            "write",
            {"website_reservation_date": False, "website_reservation_id": False},
            eta=delay,
        )
        return True

    def is_available_for_web_sponsorship(self, session_token):
        """
        Tells whether the child can be sponsored
        @param session_token: token of the user requesting the child
        @return: True/False
        """
        self.ensure_one()
        if self.website_reservation_date:
            return session_token and self.website_reservation_id == session_token
        return True

    @api.model
    def website_hold_child(self, search_params):
        """
        Called by website JS in order to fetch a new child on the global pool
        meeting the search criteria given by the user.
        @param search_params: query parameters
        @return: ids of the child records on hold
        """
        GENDER_MAP = {"M": "Male", "F": "Female"}
        child_gender = GENDER_MAP.get(search_params.get("gender"), False)
        field_offices = self.env["compassion.field.office"]
        fo_code = search_params.get("country")
        if fo_code:
            # Special case for Indonesia which has two field offices
            if fo_code == "ID":
                fo_code += ",IO"
            field_offices = field_offices.search(
                [("field_office_id", "in", fo_code.split(","))]
            )
        birthday = False
        if search_params.get("birthday"):
            birthday = fields.Date.from_string(search_params.get("birthday"))
        partner = self.env.user.partner_id
        limit = search_params.get("limit", 1)
        childpool = self.env["compassion.childpool.search"].create(
            {
                "take": limit,
                "min_age": search_params.get("age_min"),
                "max_age": search_params.get("age_max"),
                "gender": child_gender,
                "field_office_ids": field_offices and [(6, 0, field_offices.ids)],
                "birthday_month": birthday and birthday.month,
                "birthday_day": birthday and birthday.day,
                # Make sure we find what we are looking for
                # It's not a problem to take high priority children here as
                # the chance that they will be sponsored is high and the
                # e-commerce hold shouldn't be long
                "skip": 0,
            }
        )
        childpool.do_search()
        hold_wizard = (
            childpool.env["child.hold.wizard"]
            .with_context(
                active_id=childpool.id,
                active_model=childpool._name,
                default_is_published=True,  # Directly publish the child
                queue_job__no_delay=True,  # Make sure we wait for the hold to be done
            )
            .create(
                {
                    "channel": "web",
                    "ambassador": partner.id,
                    "source_code": "website_hold_child",
                    "type": HoldType.E_COMMERCE_HOLD.value,
                    "expiration_date": self.env[
                        "compassion.hold"
                    ].get_default_hold_expiration(HoldType.E_COMMERCE_HOLD),
                    "primary_owner": 1,  # Don't put the current user as owner
                }
            )
        )
        res = hold_wizard.send()
        try:
            child_ids = res["domain"][0][2]
        except IndexError as error:
            _logger.error(
                "No child found for the given search parameters: %s", str(search_params)
            )
            raise ChildNotFound(
                _("No child found for the given search parameters.")
            ) from error
        return child_ids

    def child_released(self, state="R"):
        # Unpublish the child if it's released
        self.write({"is_published": False})
        return super().child_released(state)

    def child_sponsored(self, sponsor_id):
        # Unpublish the child if it's sponsored
        self.write({"is_published": False})
        return super().child_sponsored(sponsor_id)

    def get_base_url(self):
        company = self.env.company
        website = (
            self.env["website"]
            .sudo()
            .search(
                [
                    ("company_id", "=", company.id),
                    ("is_my_compassion", "=", True),
                ],
                limit=1,
            )
        )
        if website:
            return website.domain
        return super().get_base_url()
