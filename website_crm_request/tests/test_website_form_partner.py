# Copyright (C) 2026 Compassion CH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from types import SimpleNamespace
from uuid import uuid4

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteFormPartner(TransactionCase):
    """A request sent from a website form gets its contact the way the mail
    gateway gives one to a request that arrives by e-mail.

    The two paths a contact form takes are covered end to end by
    my_compassion's contact_us tour; what is checked here is what it must not
    do when the form says too little, or says too much.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.token = uuid4().hex[:12]

    def _submit(self, email, **params):
        """Run the filter on what the website form controller would hand it:
        the whitelisted values, and the raw parameters on the request.
        """
        values = {
            "name": f"Subject {self.token}",
            "email_from": email,
            "description": "Message",
            "partner_phone": params.pop("partner_phone", False),
        }
        request = SimpleNamespace(params=dict(params, email_from=email))
        return self.env["crm.claim"].website_form_input_filter(request, values)

    def test_matches_the_contact_holding_the_address(self):
        partner = self.env["res.partner"].create(
            {
                "firstname": "Web",
                "lastname": f"Form {self.token}",
                "email": f"web.form.{self.token}@example.org",
                "lang": "en_US",
            }
        )
        values = self._submit(partner.email, firstname="Someone", lastname="Else")
        self.assertEqual(
            values["partner_id"],
            partner.id,
            "The name typed in the form must not outweigh the address it was "
            "sent from",
        )
        self.assertEqual(
            values["language"],
            partner.lang,
            "The request needs a language for the Reply button to work",
        )

    def test_creates_the_contact_of_an_unknown_address(self):
        title = self.env["res.partner.title"].search(
            [("is_shown_on_public_forms", "=", True)], order="shortcut asc", limit=1
        )
        self.assertTrue(title, "the database needs a title for the public forms")
        email = f"web.form.new.{self.token}@example.org"

        values = self._submit(
            email,
            firstname="Web",
            lastname=f"Newcomer {self.token}",
            title=title.shortcut,
            partner_phone="0041244342124",
        )

        partner = self.env["res.partner"].browse(values["partner_id"])
        self.assertEqual(partner.firstname, "Web")
        self.assertEqual(partner.lastname, f"Newcomer {self.token}")
        self.assertEqual(partner.email, email)
        self.assertEqual(partner.title, title)
        self.assertEqual(partner.phone, "0041244342124")

    def test_leaves_the_request_alone_when_nobody_signed_it(self):
        values = self._submit(f"web.form.anon.{self.token}@example.org")
        self.assertNotIn(
            "partner_id",
            values,
            "A contact needs a name: an unassigned request is better than a "
            "nameless contact",
        )

    def test_matches_one_of_our_own_addresses(self):
        # crm_request keeps Compassion's own addresses out of the rule the
        # mail gateway uses, because our address on a forwarded mail is not
        # its author. On a form the visitor typed the address themselves, so
        # it is matched like any other - and never duplicated.
        ours = self.env["res.partner"].create(
            {
                "firstname": "Compassion",
                "lastname": f"Support {self.token}",
                "email": f"support.{self.token}@compassion.ch",
            }
        )
        values = self._submit(
            ours.email, firstname="Compassion", lastname=f"Support {self.token}"
        )
        self.assertEqual(values["partner_id"], ours.id)
        self.assertEqual(
            self.env["res.partner"].search_count([("email", "=ilike", ours.email)]),
            1,
            "The address Odoo already holds must not be given a second contact",
        )
