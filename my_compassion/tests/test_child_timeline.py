from odoo import fields
from odoo.tests import TransactionCase

from odoo.addons.website.tools import MockRequest

from ..controllers.my2_children import MyCompassionChildrenController


class TestChildTimeline(TransactionCase):
    """The child timeline must read live values, not leftover columns.

    On correspondence and sponsorship_gift, the fields child_id, partner_id,
    gift_type and sponsorship_gift_type are related fields. Odoo keeps no
    database column for them, so the old columns that remain in the tables are
    empty on every record created since. A timeline query reading those columns
    drops recent letters and gifts, and crashes the gift template when the gift
    type reads as empty.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = MyCompassionChildrenController()
        # The sponsorship takes its country from the sponsor, and it is required.
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Timeline Sponsor",
                "country_id": cls.env.ref("base.se").id,
            }
        )
        project = cls.env["compassion.project"].create(
            {
                "fcp_id": "timeline_test_fcp",
                "last_update_date": fields.Date.today(),
            }
        )
        cls.child = cls.env["compassion.child"].create(
            {
                "name": "Timeline Child",
                "global_id": "timeline_test_child",
                # The sponsorship display name needs the child code.
                "local_id": "TL1234567",
                "project_id": project.id,
            }
        )
        group = cls.env["recurring.contract.group"].create(
            {"partner_id": cls.partner.id}
        )
        cls.sponsorship = cls.env["recurring.contract"].create(
            {
                "child_id": cls.child.id,
                "partner_id": cls.partner.id,
                "correspondent_id": cls.partner.id,
                "group_id": group.id,
                "pricelist_id": 1,
            }
        )
        cls.gift = cls.env["sponsorship.gift"].create(
            {
                "sponsorship_id": cls.sponsorship.id,
                "gift_type_id": cls.env.ref(
                    "sponsorship_compassion.gift_type_birthday"
                ).id,
                "amount": 30.0,
            }
        )
        # is_published is computed. A letter from the sponsor is published as
        # soon as it is not in an error state, while a letter from the child
        # waits for its sponsor communication to be sent.
        cls.letter = cls.env["correspondence"].create(
            {
                "sponsorship_id": cls.sponsorship.id,
                "partner_id": cls.partner.id,
                "direction": "Supporter To Beneficiary",
                "status_date": fields.Datetime.now(),
            }
        )

    def _timeline(self, limit=20):
        with MockRequest(self.env):
            return self.controller._get_timeline_data(
                self.child.id, self.partner.ids, 0, limit
            )

    def _count(self):
        with MockRequest(self.env):
            return self.controller._get_timeline_count(self.child.id, self.partner.ids)

    def test_gift_is_listed_with_its_type(self):
        gifts = [r for r in self._timeline() if r["model"] == "sponsorship_gift"]
        self.assertEqual(len(gifts), 1, "the sponsored child's gift must be listed")
        # The template branches on this string, so it must never be None.
        self.assertEqual(gifts[0]["metadata"], "Beneficiary Gift|Birthday")
        self.assertEqual(gifts[0]["title"], "Birthday gift")

    def test_letter_is_listed(self):
        self.assertTrue(self.letter.is_published, "fixture must be a published letter")
        letters = [r for r in self._timeline() if r["model"] == "correspondence"]
        self.assertEqual(len(letters), 1, "the child's published letter must be listed")

    def test_count_matches_the_listed_records(self):
        self.assertEqual(self._count(), len(self._timeline()))

    def test_batch_template_renders(self):
        records = self._timeline()
        self.assertTrue(records)
        with MockRequest(self.env, website=self.env.ref("my_compassion.my2_website")):
            self.env["ir.ui.view"]._render_template(
                "my_compassion.SponsorChildTimelineBatchComponent",
                {"records": records},
            )
