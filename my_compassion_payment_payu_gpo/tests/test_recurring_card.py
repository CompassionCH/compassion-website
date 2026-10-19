from odoo import Command
from odoo.tests import tagged

from odoo.addons.my_compassion.tests.common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestRecurringCard(DigitalSeamCase):
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
        # The name on the card, once typed, is sent.
        tx.payu_gpo_cardholder_name = "Anna Nowak"
        self.assertEqual(tx._payu_gpo_buyer_names(), ("Anna", "Nowak"))

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
