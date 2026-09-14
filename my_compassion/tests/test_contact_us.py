##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from uuid import uuid4

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestContactUs(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin")
        cls.admin.tour_enabled = False
        cls.admin.lang = "en_US"

        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()

        cls.title = cls.env["res.partner.title"].search(
            [("is_shown_on_public_forms", "=", True)], order="shortcut asc", limit=1
        )
        assert cls.title, "the database needs a title published on the public forms"

        cls.token = uuid4().hex[:12]
        cls.known_email = f"camille.rochat+{cls.token}@example.org"
        cls.unknown_email = f"lukas.baumann+{cls.token}@example.org"

        cls.known_partner = cls.env["res.partner"].create(
            {
                "firstname": "Camille",
                "lastname": "Rochat",
                "email": cls.known_email,
            }
        )

    def test_contact_us(self):
        claim_obj = self.env["crm.claim"]
        last_id = claim_obj.search([], order="id desc", limit=1).id

        self.start_tour(
            f"/contactus?tour_token={self.token}",
            "contact_us",
            login="admin",
            timeout=180,
        )

        requests = claim_obj.search([("id", ">", last_id)], order="id")
        self.assertEqual(
            len(requests), 2, "The tour should have sent two messages to the Support"
        )
        known_request, unknown_request = requests

        # The message of the contact Odoo already had.
        self.assertEqual(known_request.name, f"Change of payment date - {self.token}")
        self.assertEqual(known_request.email_from, self.known_email)
        self.assertEqual(known_request.partner_phone, "0041216541288")
        self.assertIn(
            "I would like to change the date my monthly payment is taken.",
            known_request.description,
        )
        self.assertEqual(
            known_request.partner_id,
            self.known_partner,
            "The request should be attached to the contact that already existed",
        )

        # The message of the contact Odoo had to create.
        self.assertEqual(unknown_request.name, f"Sponsoring a child - {self.token}")
        self.assertEqual(unknown_request.email_from, self.unknown_email)
        self.assertEqual(unknown_request.partner_phone, "0041313017654")
        self.assertIn(
            "I would like to sponsor a child and do not know where to start.",
            unknown_request.description,
        )

        new_partner = unknown_request.partner_id
        self.assertTrue(
            new_partner, "The second request should have created a new contact"
        )
        # The contact holds what the form was filled with.
        self.assertEqual(new_partner.firstname, "Lukas")
        self.assertEqual(new_partner.lastname, "Baumann")
        self.assertEqual(new_partner.email, self.unknown_email)
        self.assertEqual(new_partner.title, self.title)
        self.assertEqual(new_partner.phone, "0041313017654")
