from odoo import Command
from odoo.tests import tagged

from odoo.addons.my_compassion.controllers.my2_update_card import (
    MyCompassionUpdateCard,
)

from .common import PayuDigitalCase


@tagged("post_install", "-at_install")
class TestRecurringCard(PayuDigitalCase):
    def _transaction(self, contract, reference, **values):
        return self.env["payment.transaction"].create(
            {
                "provider_id": contract.payment_mode_id.payment_provider_id.id,
                "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
                "partner_id": contract.partner_id.id,
                "amount": 10.0,
                "currency_id": contract.company_id.currency_id.id,
                "reference": reference,
                **values,
            }
        )

    def test_sponsorship_cards_are_recurring(self):
        contract = self._make_digital_contract()
        invoice = contract._ensure_first_invoice()
        first_payment = self._transaction(
            contract, "payu-bridge-first", invoice_ids=[Command.set(invoice.ids)]
        )
        self.assertTrue(first_payment._payu_gpo_card_is_recurring())
        card_update = self._transaction(
            contract,
            "payu-bridge-update",
            my2_card_update_group_id=contract.group_id.id,
        )
        self.assertTrue(card_update._payu_gpo_card_is_recurring())

    def test_other_cards_are_cards_on_file(self):
        contract = self._make_digital_contract()
        donation = self._transaction(contract, "payu-bridge-donation")
        self.assertFalse(donation._payu_gpo_card_is_recurring())

    def test_card_the_group_does_not_take_is_on_file(self):
        # An overdue invoice paid from the portal: the group keeps its card,
        # so the new one is never charged monthly.
        contract, invoice, _token = self._make_chargeable_invoice()
        overdue_payment = self._transaction(
            contract, "payu-bridge-overdue", invoice_ids=[Command.set(invoice.ids)]
        )
        self.assertFalse(overdue_payment._payu_gpo_card_is_recurring())
        # The update-card page pays the same invoice with a card that
        # replaces the group's.
        _overrides, values = MyCompassionUpdateCard._update_card_tx_values(
            contract.group_id, invoice
        )
        card_update = self._transaction(contract, "payu-bridge-arrears", **values)
        self.assertTrue(card_update._payu_gpo_card_is_recurring())

    def test_card_the_group_cannot_charge_is_on_file(self):
        contract, _invoice, _token = self._make_chargeable_invoice()
        group = contract.group_id
        providers = self._providers_the_group_cannot_charge_with(group)
        for reason, provider in providers.items():
            with self.subTest(provider=reason):
                tx = self.env["payment.transaction"].create(
                    {
                        "provider_id": provider.id,
                        "payment_method_id": self.env.ref(
                            "payment.payment_method_unknown"
                        ).id,
                        "partner_id": contract.partner_id.id,
                        "reference": f"payu-bridge-{reason}-provider",
                        "amount": 10.0,
                        "currency_id": provider.company_id.currency_id.id,
                        "my2_card_update_group_id": group.id,
                    }
                )
                self.assertFalse(tx._payu_gpo_card_is_recurring())

    def test_card_for_a_group_of_another_company_is_on_file(self):
        contract, _invoice, _token = self._make_payu_chargeable_invoice()
        group = contract.group_id
        provider = group.payment_mode_id.payment_provider_id
        self._move_to_another_company(group)
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_card").id,
                "partner_id": contract.partner_id.id,
                "reference": "payu-bridge-moved-group",
                "amount": 10.0,
                "currency_id": provider.company_id.currency_id.id,
                "my2_card_update_group_id": group.id,
            }
        )
        self.assertNotEqual(group.company_id, tx.company_id)
        self.assertFalse(tx._payu_gpo_card_is_recurring())

    def test_update_card_page_saves_a_payu_card_with_a_payment(self):
        contract, invoice, _token = self._make_payu_chargeable_invoice()
        group = contract.group_id
        provider = group.payment_mode_id.payment_provider_id
        self.assertEqual(
            MyCompassionUpdateCard._update_card_provider(group, invoice), provider
        )
        # PayU makes no card validation (zero-amount order)
        self.assertFalse(
            MyCompassionUpdateCard._update_card_provider(group, invoice.browse())
        )

    # === The payer's name ===

    def test_no_placeholder_name_sent_to_payu(self):
        contract = self._make_digital_contract()
        partner = contract.partner_id
        partner.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        tx = self._transaction(contract, "payu-bridge-names")
        self.assertEqual(tx._payu_gpo_buyer_names(), ("", ""))
        # The names on the card, once typed, are sent as typed.
        tx.write(
            {
                "payu_gpo_cardholder_name": "Jan Kowalski Nowak",
                "payu_gpo_cardholder_firstname": "Jan",
                "payu_gpo_cardholder_lastname": "Kowalski Nowak",
            }
        )
        self.assertEqual(tx._payu_gpo_buyer_names(), ("Jan", "Kowalski Nowak"))
        # and replace the placeholder as typed, once paid.
        tx._my2_apply_cardholder_name()
        self.assertEqual(
            (partner.firstname, partner.lastname), ("Jan", "Kowalski Nowak")
        )
        self.assertFalse(partner.my2_name_placeholder)

    def test_cardholder_name(self):
        contract = self._make_digital_contract()
        tx = self._transaction(contract, "payu-bridge-cardholder")
        # PayU's echo of the buyer; the placeholder is no name
        self.assertEqual(
            tx._my2_cardholder_name_payu_gpo(
                {"order": {"buyer": {"firstName": "Anna", "lastName": "Nowak"}}}
            ),
            "Anna Nowak",
        )
        placeholder = self.env["res.partner"].MY2_PLACEHOLDER_NAME
        self.assertEqual(
            tx._my2_cardholder_name_payu_gpo(
                {"order": {"buyer": {"firstName": placeholder, "lastName": ""}}}
            ),
            "",
        )
        self.assertEqual(tx._my2_cardholder_name_payu_gpo({"order": {}}), "")
        # The name typed on the card comes first: PayU's status read may
        # carry no buyer while the payment waits.
        tx.payu_gpo_cardholder_name = "Jan Kowalski"
        self.assertEqual(
            tx._my2_cardholder_name_payu_gpo({"order": {}}), "Jan Kowalski"
        )
