##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import datetime, timedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFundraiserSource(TransactionCase):
    """A fundraiser is the source of the sponsorships they bring."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        now = datetime.now()
        cls.compassion_event = cls.env["crm.event.compassion"].create(
            {
                "name": "Fundraiser source trip",
                "type": "tour",
                "start_date": now,
                "end_date": now + timedelta(days=1),
                "hold_start_date": now.date(),
                "user_id": cls.env.uid,
            }
        )
        cls.event = cls.env["event.event"].create(
            {
                "name": "Fundraiser source trip",
                "date_begin": now,
                "date_end": now + timedelta(days=1),
                "compassion_event_id": cls.compassion_event.id,
                "fundraising": True,
            }
        )
        cls.fundraiser = cls.env["res.partner"].create(
            {"name": "Fundraiser source runner"}
        )
        cls.sponsor = cls.env["res.partner"].create(
            {
                "name": "Fundraiser source sponsor",
                "country_id": cls.env.ref("base.ch").id,
            }
        )
        cls.registration = cls.env["event.registration"].create(
            {"event_id": cls.event.id, "partner_id": cls.fundraiser.id}
        )
        cls.group = cls.env["recurring.contract.group"].create(
            {
                "partner_id": cls.sponsor.id,
                "advance_billing_months": 1,
                "recurring_value": 1,
                "recurring_unit": "month",
            }
        )

    def _contract(self, **vals):
        return self.env["recurring.contract"].create(
            {
                "type": "O",
                "partner_id": self.sponsor.id,
                "group_id": self.group.id,
                "origin_id": self.compassion_event.origin_id.id,
                **vals,
            }
        )

    def test_registration_gets_source(self):
        self.assertIn(self.fundraiser.name, self.registration.source_id.name)

    def test_no_source_without_fundraising(self):
        self.event.fundraising = False
        other = self.env["event.registration"].create(
            {"event_id": self.event.id, "partner_id": self.sponsor.id}
        )
        self.assertFalse(other.source_id)

    def test_sponsorship_takes_fundraiser_source(self):
        contract = self._contract(ambassador_id=self.fundraiser.id)
        self.assertEqual(contract.registration_id, self.registration)
        # The fundraiser replaces the source of the event
        self.assertEqual(contract.source_id, self.registration.source_id)
        self.assertNotEqual(contract.source_id, self.compassion_event.source_id)

    def test_sponsorship_keeps_own_source(self):
        own = self.env["utm.source"].create({"name": "Fundraiser source own"})
        contract = self._contract(ambassador_id=self.fundraiser.id, source_id=own.id)
        self.assertEqual(contract.source_id, own)

    def test_ambassador_set_later(self):
        contract = self._contract()
        self.assertEqual(contract.source_id, self.compassion_event.source_id)
        contract.ambassador_id = self.fundraiser
        self.assertEqual(contract.source_id, self.registration.source_id)
