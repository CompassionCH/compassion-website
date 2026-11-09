import re
from datetime import date, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import HttpCase

CHILD_LINK_RE = re.compile(r"/my2/new-sponsorship/(\d+)\?")

# (key, field office, unsponsored_since), created in this order so that the
# ids break the ties of equal dates in this order too.
# Field offices QC and QD are in the same country.
CHILDREN = [
    ("ke1", "QA", "2019-01-01"),
    ("ke2", "QA", "2019-02-01"),
    ("ke3", "QA", "2019-03-01"),
    ("ke4", "QA", False),
    ("pe1", "QB", "2020-01-01"),
    ("pe2", "QB", "2020-02-01"),
    ("id_c", "QC", "2020-03-01"),
    ("id_d", "QD", "2019-02-01"),  # same date as ke2, created after it
]
FIELD_OFFICE_COUNTRIES = {
    "QA": "base.ke",
    "QB": "base.pe",
    "QC": "base.id",
    "QD": "base.id",
}

WAITING = ["ke1", "ke2", "id_d", "ke3", "pe1", "pe2", "id_c", "ke4"]
# Round 1: the first child of each country, round 2 the second, and so on;
# within a round, the waiting order. Indonesia (QC and QD) is one country.
MIX_COUNTRIES = ["ke1", "id_d", "pe1", "ke2", "pe2", "id_c", "ke3", "ke4"]


def create_waiting_children(env, prefix):
    """Create the CHILDREN, each available with an active hold and
    published, and return them as {key: child}."""
    field_offices = {
        code: env["compassion.field.office"].create(
            {
                "field_office_id": code,
                "name": f"Child Order {code}",
                "country_id": env.ref(country).id,
            }
        )
        for code, country in FIELD_OFFICE_COUNTRIES.items()
    }
    children = {}
    # Creating a project asks GMC for its details and creating a child fetches
    # its pictures: neither is what this test is about.
    with (
        patch.object(
            env.registry["compassion.project"], "update_informations", lambda s: True
        ),
        patch.object(
            env.registry["compassion.child"], "update_child_pictures", lambda s: None
        ),
    ):
        projects = {
            code: env["compassion.project"].create(
                {"fcp_id": f"{code}9{prefix}01", "last_update_date": date.today()}
            )
            for code in field_offices
        }
        for index, (key, code, since) in enumerate(CHILDREN):
            # The project takes its field office from its code
            assert projects[code].field_office_id == field_offices[code]
            children[key] = env["compassion.child"].create(
                {
                    "name": f"Child Order {key}",
                    "preferred_name": f"Child Order {key}",
                    "global_id": f"child_order_{prefix}_{key}",
                    "local_id": f"{code}{prefix}{index:04d}",
                    "project_id": projects[code].id,
                    "birthdate": date.today() - timedelta(days=8 * 365),
                    "gender": "F",
                    "unsponsored_since": since,
                    "state": env["compassion.child"]._available_states()[0],
                    "is_published": True,
                }
            )
    for child in children.values():
        hold = env["compassion.hold"].create(
            {
                "child_id": child.id,
                "type": "E-Commerce Hold",
                "state": "active",
                "expiration_date": fields.Datetime.now() + timedelta(days=1),
            }
        )
        child.hold_id = hold
    return children


@tagged("post_install", "-at_install")
class TestChildListOrder(TransactionCase):
    """The list of children waiting for a sponsor is ordered by the
    strategy the website's setting names, in a stable order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.children = create_waiting_children(cls.env, "11")
        cls.keys = {child.id: key for key, child in cls.children.items()}
        cls.domain = [("id", "in", [c.id for c in cls.children.values()])]
        cls.website = cls.env["website"].create({"name": "Child Order Website"})

    def _page(self, order, limit=None, offset=0):
        self.website.my2_child_list_order = order
        children, total = self.env["compassion.child"]._my2_available_children(
            self.domain, limit, offset, self.website
        )
        return [self.keys[child.id] for child in children], total

    def test_default_is_longest_waiting_first(self):
        self.assertEqual(self.website.my2_child_list_order, "waiting")
        children, total = self.env["compassion.child"]._my2_available_children(
            self.domain, None, 0, self.website
        )
        self.assertEqual([self.keys[child.id] for child in children], WAITING)
        self.assertEqual(total, len(CHILDREN))

    def test_mix_countries_takes_each_country_in_turn(self):
        self.assertEqual(self._page("mix_countries"), (MIX_COUNTRIES, len(CHILDREN)))

    def test_pages_are_disjoint_and_cover_the_list(self):
        for order, expected in (("waiting", WAITING), ("mix_countries", MIX_COUNTRIES)):
            with self.subTest(order=order):
                pages = []
                for offset in range(0, len(CHILDREN), 3):
                    page, total = self._page(order, limit=3, offset=offset)
                    self.assertEqual(total, len(CHILDREN))
                    pages.append(page)
                self.assertEqual([len(page) for page in pages], [3, 3, 2])
                self.assertEqual(sum(pages, []), expected)

    def test_mix_countries_keeps_the_domain(self):
        self.domain = self.domain + [
            ("field_office_id.field_office_id", "in", ["QB", "QD"])
        ]
        self.assertEqual(self._page("mix_countries"), (["id_d", "pe1", "pe2"], 3))

    def test_mix_countries_of_no_child(self):
        self.domain = [("id", "=", 0)]
        self.assertEqual(self._page("mix_countries", limit=3), ([], 0))


@tagged("post_install", "-at_install")
class TestChildListOrderRoute(HttpCase):
    """/my2/sponsorships/fetch renders the page of the website's order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        cls.children = create_waiting_children(cls.env, "12")
        cls.keys = {child.id: key for key, child in cls.children.items()}
        # Only this test's children are on the list
        cls.env["compassion.child"].search(
            [("is_published", "=", True), ("id", "not in", list(cls.keys))]
        ).write({"is_published": False})

    def _fetch(self, order, offset):
        self.website.my2_child_list_order = order
        result = self.make_jsonrpc_request(
            "/my2/sponsorships/fetch", {"limit": 3, "offset": offset}
        )
        self.assertEqual(set(result), {"html", "count", "total"})
        keys = [self.keys[int(i)] for i in CHILD_LINK_RE.findall(result["html"])]
        self.assertEqual(result["count"], len(keys))
        self.assertEqual(result["total"], len(CHILDREN))
        return keys

    def test_fetch_follows_the_website_order(self):
        for order, expected in (("waiting", WAITING), ("mix_countries", MIX_COUNTRIES)):
            with self.subTest(order=order):
                self.assertEqual(self._fetch(order, 0), expected[:3])
                self.assertEqual(self._fetch(order, 3), expected[3:6])
