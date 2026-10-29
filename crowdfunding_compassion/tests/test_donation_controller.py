from datetime import timedelta

from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDonationController(HttpCase):
    def setUp(self):
        super().setUp()
        project = self.env["crowdfunding.project"].create(
            {
                "name": "Donation page project",
                "type": "collective",
                "project_owner_id": self.env.ref("base.res_partner_address_15").id,
                "deadline": fields.Date.today() + timedelta(weeks=1),
                "website_published": True,
            }
        )
        self.url = f"/project/{project.id}/donation"

    def test_page_must_be_a_number(self):
        for page in ("1 ORDER BY 1-- -", "1' OR '1'='1", "2.5", "abc"):
            response = self.url_open(self.url, params={"page": page})
            self.assertEqual(response.status_code, 400, page)

    def test_participant_must_be_a_number(self):
        response = self.url_open(
            self.url, params={"page": 2, "participant": "1) AND (1=1"}
        )
        self.assertEqual(response.status_code, 400)

    def test_numeric_page_still_works(self):
        response = self.url_open(self.url, params={"page": 2})
        self.assertEqual(response.status_code, 200)
