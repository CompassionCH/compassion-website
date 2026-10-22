from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.website.tools import MockRequest

from ..controllers.my2_update_card import MyCompassionUpdateCard
from ..controllers.website_utils import ensure_recurring_instrument
from .common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestRecurringInstrument(DigitalSeamCase):
    """The my2 payment pages must always end with a saved card.

    Locks down the transaction guard and the update-card form mode. Both
    exist because the monthly off-session charge has nothing to charge
    without a token on the group.
    """

    def _make_tx(self, contract, invoice, **extra):
        provider = contract.payment_mode_id.payment_provider_id
        method = self.env.ref("payment.payment_method_unknown")
        return self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "reference": f"guard-{contract.id}-{len(extra)}",
                "amount": 100.0,
                "currency_id": invoice.currency_id.id,
                "partner_id": contract.partner_id.id,
                **extra,
            }
        )

    def test_guard_rejects_transaction_without_instrument(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        tx = self._make_tx(contract, invoice, tokenize=False)
        with MockRequest(self.env), self.assertRaises(ValidationError):
            ensure_recurring_instrument(tx)

    def test_guard_accepts_tokenizing_transaction(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        tx = self._make_tx(contract, invoice, tokenize=True)
        with MockRequest(self.env):
            ensure_recurring_instrument(tx)

    def test_guard_accepts_saved_token_payment(self):
        contract, invoice, token = self._make_chargeable_invoice()
        tx = self._make_tx(contract, invoice, tokenize=False, token_id=token.id)
        with MockRequest(self.env):
            ensure_recurring_instrument(tx)

    def test_update_card_mode_follows_amount_due(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        group = contract.group_id
        provider = group.payment_mode_id.payment_provider_id
        with MockRequest(self.env):
            due = MyCompassionUpdateCard._get_update_card_values(
                group, provider, None, invoice
            )
            nothing_due = MyCompassionUpdateCard._get_update_card_values(
                group, provider, None, invoice.browse()
            )
        self.assertEqual(due["mode"], "payment")
        self.assertEqual(due["amount"], invoice.amount_residual)
        self.assertEqual(nothing_due["mode"], "validation")
        self.assertEqual(nothing_due["amount"], 0)

    def test_update_card_payment_replaces_the_card(self):
        """With arrears, the new card pays them and replaces the group's
        card: the next monthly charges use it."""
        contract, invoice, token = self._make_chargeable_invoice()
        group = contract.group_id
        overrides, create_values = MyCompassionUpdateCard._update_card_tx_values(
            group, group._due_digital_invoices()
        )
        new_card = token.copy({"provider_ref": "update-card-new-card"})
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": token.provider_id.id,
                "payment_method_id": token.payment_method_id.id,
                "partner_id": group.partner_id.id,
                "reference": "update-card-arrears",
                "amount": overrides["amount"],
                "currency_id": overrides["currency_id"],
                "operation": "online_direct",
                "token_id": new_card.id,
                **create_values,
            }
        )
        tx._set_done()
        tx._post_process()
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.assertEqual(group.payment_token_id, new_card)
