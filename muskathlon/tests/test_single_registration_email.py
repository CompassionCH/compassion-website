##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSingleRegistrationEmail(TransactionCase):
    """The responsible of a Muskathlon gets one e-mail per registration, the
    one with all the details (T3647)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.responsible = new_test_user(
            cls.env,
            login="t3647_responsible",
            email="t3647-responsible@example.com",
            context={"no_reset_password": True},
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "T3647 participant", "email": "t3647-participant@example.com"}
        )

    def create_event(self, event_type):
        # The responsible follows the event, without the "assigned" notice.
        event = (
            self.env["event.event"]
            .with_context(mail_auto_subscribe_no_notify=True)
            .create(
                {
                    "name": "T3647 event",
                    "event_type_id": event_type.id,
                    "date_begin": "2030-05-01 08:00:00",
                    "date_end": "2030-05-10 18:00:00",
                    "user_id": self.responsible.id,
                }
            )
        )
        self.assertIn(self.responsible.partner_id, event.message_partner_ids)
        event.compassion_event_id = self.env["crm.event.compassion"].create(
            {
                "name": "T3647 event",
                "type": "sport",
                "start_date": "2030-05-01 08:00:00",
                "end_date": "2030-05-10 18:00:00",
                "hold_start_date": "2030-04-01",
                "odoo_event_id": event.id,
            }
        )
        return event

    def register(self, event):
        return self.env["event.registration"].create(
            {"event_id": event.id, "partner_id": self.partner.id}
        )

    def messages_to_responsible(self, records):
        return self.env["mail.message"].search(
            [
                ("model", "=", records._name),
                ("res_id", "in", records.ids),
                (
                    "notification_ids.res_partner_id",
                    "=",
                    self.responsible.partner_id.id,
                ),
            ]
        )

    def test_muskathlon_one_email(self):
        event = self.create_event(self.env.ref("muskathlon.event_type_muskathlon"))
        registration = self.register(event)
        self.assertTrue(registration.is_muskathlon)

        self.assertFalse(
            self.messages_to_responsible(event),
            "No 'New registration' note on the event",
        )
        details = self.messages_to_responsible(registration)
        self.assertEqual(len(details), 1)
        self.assertIn("New Muskathlon registration", details.subject)

    def test_responsible_not_following_the_event(self):
        event = self.create_event(self.env.ref("muskathlon.event_type_muskathlon"))
        event.message_unsubscribe(self.responsible.partner_id.ids)

        registration = self.register(event)

        self.assertEqual(len(self.messages_to_responsible(registration)), 1)

    def test_other_events_keep_the_note(self):
        other_type = self.env["event.type"].create({"name": "T3647 trip"})
        event = self.create_event(other_type)
        registration = self.register(event)
        self.assertFalse(registration.is_muskathlon)

        note = self.messages_to_responsible(event)
        self.assertEqual(len(note), 1)
        self.assertIn("New registration", note.body)
