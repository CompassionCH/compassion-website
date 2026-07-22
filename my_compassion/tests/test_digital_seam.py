from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDigitalSeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Digital Seam Test Co"})
        cls.partner = cls.env["res.partner"].create({"name": "Digital Seam Sponsor"})
        cls.pay_method = cls.env.ref("my_compassion.payment_method_psp_token")
        cls.mode = cls.env["account.payment.mode"].create(
            {
                "name": "Digital Seam Test Mode",
                "company_id": cls.company.id,
                "bank_account_link": "variable",
                "payment_method_id": cls.pay_method.id,
                "payment_order_ok": False,
            }
        )

    def test_find_or_create_group_is_idempotent(self):
        Group = self.env["recurring.contract.group"]
        g1 = Group._find_or_create_group(self.partner, self.company, self.mode)
        g2 = Group._find_or_create_group(self.partner, self.company, self.mode)
        self.assertEqual(g1, g2)
        self.assertEqual(g1.partner_id, self.partner)
        self.assertEqual(g1.company_id, self.company)
        self.assertEqual(g1.payment_mode_id, self.mode)

    def test_find_or_create_group_modeless(self):
        Group = self.env["recurring.contract.group"]
        empty_mode = self.env["account.payment.mode"]
        g = Group._find_or_create_group(self.partner, self.company, empty_mode)
        self.assertFalse(g.payment_mode_id)
        self.assertEqual(g.company_id, self.company)
        # mode-less and mode-ful groups are distinct
        g_mode = Group._find_or_create_group(self.partner, self.company, self.mode)
        self.assertNotEqual(g, g_mode)

    def test_token_company_constraint(self):
        other_company = self.env["res.company"].create(
            {"name": "Digital Seam Other Co"}
        )
        provider = self.env["payment.provider"].create(
            {
                "name": "Digital Seam Provider",
                "code": "none",
                "company_id": other_company.id,
            }
        )
        psp_method = self.env["payment.method"].search([], limit=1)
        token = self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": psp_method.id,
                "partner_id": self.partner.id,
                "provider_ref": "digital-seam-test-ref",
                "payment_details": "1234",
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            self.partner, self.company, self.mode
        )
        # token belongs to other_company, group to cls.company -> must be rejected
        with self.assertRaises(ValidationError):
            group.payment_token_id = token

    def test_validated_payment_mode_rejects_foreign_company(self):
        # company created before new(): creating a company clears the ORM
        # cache, which would wipe the in-memory new() record's values
        other = self.env["res.company"].create({"name": "Digital Seam Foreign Co"})
        self.mode.is_published = True
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(other)

    def test_validated_payment_mode_rejects_unpublished(self):
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        self.mode.is_published = False
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(self.company)

    def test_validated_payment_mode_rejects_archived(self):
        # archived modes are never offered by the render domain; a directly
        # posted id must not slip through either
        self.mode.is_published = True
        self.mode.active = False
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        with self.assertRaises(ValidationError):
            wizard._get_validated_payment_mode(self.company)

    def test_validated_payment_mode_accepts_published_same_company(self):
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "standard", "payment_method": self.mode.id}
        )
        self.mode.is_published = True
        self.assertEqual(
            wizard._get_validated_payment_mode(self.company), self.mode
        )

    def test_validated_payment_mode_empty_selection(self):
        # flows without a payment step (e.g. Write&Pray) post no mode and
        # must yield an empty recordset, not an error
        wizard = self.env["new.sponsorship.wizard"].new(
            {"sponsorship_type": "write_and_pray"}
        )
        self.assertFalse(wizard._get_validated_payment_mode(self.company))
