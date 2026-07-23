from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import hmac as hmac_tool

from ..models.contract_group import UPDATE_CARD_TOKEN_SCOPE
from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestDigitalFixit(DigitalSeamCase):
    """Charge-failure dunning engine and portal invitation seam.

    The engine is dormant in this module: tests supply the communication
    configs through the country hooks, exactly like a country module does.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_model = cls.env["partner.communication.job"]
        cls.first_config = cls._make_communication_config(
            "Fixit Test First", "sponsorship_compassion.model_recurring_contract"
        )
        cls.final_config = cls._make_communication_config(
            "Fixit Test Final", "sponsorship_compassion.model_recurring_contract"
        )
        cls.invitation_config = cls._make_communication_config(
            "Fixit Test Invitation", "base.model_res_partner"
        )

    @classmethod
    def _make_communication_config(cls, name, model_ref):
        template = cls.env["mail.template"].create(
            {
                "name": name,
                "model_id": cls.env.ref(
                    "partner_communication.model_partner_communication_job"
                ).id,
                "subject": name,
                "body_html": f"<p>{name}</p>",
            }
        )
        return cls.env["partner.communication.config"].create(
            {
                "name": name,
                "model_id": cls.env.ref(model_ref).id,
                "send_mode": "digital",
                "email_template_id": template.id,
            }
        )

    def _patched_fixit_configs(self):
        configs = {"first": self.first_config, "final": self.final_config}
        return patch.object(
            self.registry["recurring.contract"],
            "_my2_fixit_configs",
            lambda contracts: configs,
        )

    def _patched_invitation_config(self):
        config = self.invitation_config
        return patch.object(
            self.registry["recurring.contract"],
            "_my2_portal_invitation_config",
            lambda contracts: config,
        )

    def _fixit_jobs(self, config):
        return self.job_model.search([("config_id", "=", config.id)])

    # ------------------------------------------------------------------
    # fix-it pipeline
    # ------------------------------------------------------------------

    def test_fixit_dormant_without_configs(self):
        """No country configs (the CH situation): failures only log.

        The hook is forced empty because a country module supplying real
        configs may be installed on the test database.
        """
        contract, invoice, _token = self._make_chargeable_invoice()
        before = self.job_model.search_count([])
        with patch.object(
            self.registry["recurring.contract"],
            "_my2_fixit_configs",
            lambda contracts: {},
        ):
            contract._on_digital_charge_failed(invoice, "declined")
        self.assertEqual(self.job_model.search_count([]), before)

    def test_fixit_first_email_once_per_episode(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            jobs = self._fixit_jobs(self.first_config)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs.partner_id, contract.partner_id)
            self.assertIn(contract, jobs.get_objects())
            # a second failure in the same episode (e.g. next month's
            # invoice on the same broken card) must not mail again
            contract._on_digital_charge_failed(invoice, "declined again")
            self.assertEqual(len(self._fixit_jobs(self.first_config)), 1)

    def test_fixit_first_email_resent_after_episode(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            job = self._fixit_jobs(self.first_config)
            # The episode is over, the email was sent long ago. A pending
            # job would instead absorb the new send, because jobs merge
            # by partner and config.
            job.state = "done"
            self.env.cr.execute(
                "UPDATE partner_communication_job SET create_date = %s"
                " WHERE id = %s",
                [
                    fields.Datetime.now()
                    - timedelta(days=contract.FIXIT_EPISODE_DAYS + 1),
                    job.id,
                ],
            )
            job.invalidate_recordset(["create_date"])
            contract._on_digital_charge_failed(invoice, "declined again")
            self.assertEqual(len(self._fixit_jobs(self.first_config)), 2)

    def _age_first_job(self, job, days):
        job.write(
            {
                "state": "done",
                "sent_date": fields.Datetime.now() - timedelta(days=days),
            }
        )

    def test_fixit_escalation_after_delay(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        # Unpaid invoices pile up on live contracts. The cron only
        # escalates those.
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            self._age_first_job(
                self._fixit_jobs(self.first_config),
                contract.FIXIT_ESCALATION_DAYS + 1,
            )
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            final_jobs = self._fixit_jobs(self.final_config)
            self.assertEqual(len(final_jobs), 1)
            activities = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "recurring.contract"),
                    ("res_id", "=", contract.id),
                ]
            )
            self.assertTrue(activities)
            # idempotent: the next daily run must not escalate again
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            self.assertEqual(len(self._fixit_jobs(self.final_config)), 1)

    def test_fixit_no_escalation_before_delay(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            self._age_first_job(self._fixit_jobs(self.first_config), 5)
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            self.assertFalse(self._fixit_jobs(self.final_config))

    def test_fixit_no_escalation_when_arrears_cleared(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            self._age_first_job(
                self._fixit_jobs(self.first_config),
                contract.FIXIT_ESCALATION_DAYS + 1,
            )
            invoice.button_cancel()
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            self.assertFalse(self._fixit_jobs(self.final_config))

    def test_fixit_no_first_email_for_inactive_or_settled(self):
        """The provider can give up weeks after the refusal. A contract
        terminated in between, or one with nothing due anymore, must not
        be dunned."""
        contract, invoice, _token = self._make_chargeable_invoice()
        with self._patched_fixit_configs():
            # Still waiting, never activated. No dunning.
            contract._on_digital_charge_failed(invoice, "declined")
            self.assertFalse(self._fixit_jobs(self.first_config))
            contract.contract_active()
            invoice.button_cancel()
            # Active but nothing due anymore. No dunning either.
            contract._on_digital_charge_failed(invoice, "declined")
            self.assertFalse(self._fixit_jobs(self.first_config))

    def test_fixit_cancelled_job_latches_episode(self):
        """Staff cancelling a dunning email is a decision: the episode
        must not resend it on the next failure."""
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            self._fixit_jobs(self.first_config).write({"state": "cancel"})
            contract._on_digital_charge_failed(invoice, "declined again")
            self.assertEqual(len(self._fixit_jobs(self.first_config)), 1)

    def test_fixit_escalation_latches_on_failed_final(self):
        """A render-crashed final job must not re-escalate (and re-flag
        staff) every day."""
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        with self._patched_fixit_configs():
            contract._on_digital_charge_failed(invoice, "declined")
            self._age_first_job(
                self._fixit_jobs(self.first_config),
                contract.FIXIT_ESCALATION_DAYS + 1,
            )
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            self._fixit_jobs(self.final_config).write({"state": "failure"})
            self.env["mail.activity"].search(
                [
                    ("res_model", "=", "recurring.contract"),
                    ("res_id", "=", contract.id),
                ]
            ).unlink()
            self.env["recurring.contract"]._cron_digital_fixit_escalation()
            self.assertEqual(len(self._fixit_jobs(self.final_config)), 1)
            self.assertFalse(
                self.env["mail.activity"].search_count(
                    [
                        ("res_model", "=", "recurring.contract"),
                        ("res_id", "=", contract.id),
                    ]
                )
            )

    # ------------------------------------------------------------------
    # portal invitation
    # ------------------------------------------------------------------

    def test_portal_invitation_guards(self):
        contract = self._make_digital_contract()
        partner = contract.partner_id
        with self._patched_invitation_config():
            # no email: nothing
            contract._my2_send_portal_invitation()
            self.assertFalse(self._fixit_jobs(self.invitation_config))
            partner.email = "fixit-sponsor@example.com"
            contract._my2_send_portal_invitation()
            jobs = self._fixit_jobs(self.invitation_config)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs.partner_id, partner)
            # signup_prepare marks the partner. The token itself is
            # computed on the fly by _get_signup_url.
            self.assertEqual(partner.sudo().signup_type, "signup")
            # once ever
            contract._my2_send_portal_invitation()
            self.assertEqual(len(self._fixit_jobs(self.invitation_config)), 1)

    def test_portal_invitation_skips_existing_user(self):
        contract = self._make_digital_contract()
        partner = contract.partner_id
        partner.email = "fixit-user@example.com"
        self.env["res.users"].create(
            {
                "name": partner.name,
                "login": partner.email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        with self._patched_invitation_config():
            contract._my2_send_portal_invitation()
            self.assertFalse(self._fixit_jobs(self.invitation_config))

    def test_portal_invitation_triggers(self):
        """Digital signups are invited on activation (first payment), not
        at the waiting transition of the pay-click. Bank signups are
        invited on staff validation. Non-wizard contracts never are."""
        contract = self._make_digital_contract()
        contract.partner_id.email = "fixit-trigger@example.com"
        with self._patched_invitation_config():
            # not a wizard signup: no invitation anywhere
            contract._ensure_first_invoice()
            self.assertFalse(self._fixit_jobs(self.invitation_config))
            contract.my2_signup = True
            # digital + waiting: still nothing (no payment yet)
            contract.contract_waiting()
            self.assertFalse(self._fixit_jobs(self.invitation_config))
            contract.contract_active()
            self.assertEqual(len(self._fixit_jobs(self.invitation_config)), 1)

    def test_portal_invitation_trigger_bank_waiting(self):
        journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
        company = journal.company_id
        bank_mode = self.env["account.payment.mode"].create(
            {
                "name": "Fixit Bank Mode",
                "company_id": company.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Fixit Bank Sponsor",
                "email": "fixit-bank@example.com",
                "country_id": self.env.ref("base.se").id,
            }
        )
        group = self.env["recurring.contract.group"]._find_or_create_group(
            partner, company, bank_mode
        )
        product = self.env["product.product"].search(
            [("default_code", "=", "sponsorship")], limit=1
        )
        contract = (
            self.env["recurring.contract"]
            .with_context(no_upsert=True)
            .create(
                {
                    "partner_id": partner.id,
                    "group_id": group.id,
                    "type": "O",
                    "my2_signup": True,
                    "contract_line_ids": [
                        (0, 0, {"product_id": product.id, "amount": 100}),
                    ],
                }
            )
        )
        with self._patched_invitation_config():
            contract.contract_waiting()
            self.assertEqual(len(self._fixit_jobs(self.invitation_config)), 1)

    # ------------------------------------------------------------------
    # update-card URL helper
    # ------------------------------------------------------------------

    def test_update_card_url(self):
        contract = self._make_digital_contract()
        group = contract.group_id
        url = group._my2_update_card_url()
        self.assertIn(f"/my2/update-card?group_id={group.id}&access_token=", url)
        token = url.rsplit("access_token=", 1)[1]
        # This is what payment_utils.check_access_token will compare the
        # token against when the controller verifies the link.
        expected = hmac_tool(
            self.env(su=True),
            "generate_access_token",
            f"{UPDATE_CARD_TOKEN_SCOPE}|{group.id}|{group.partner_id.id}",
        )
        self.assertEqual(token, expected)
