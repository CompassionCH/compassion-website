from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.website.tools import MockRequest

from ..controllers.my2_update_card import MyCompassionUpdateCard
from ..controllers.website_utils import ensure_recurring_instrument
from .common import DigitalSeamCase


def without_card_validation(registry, provider):
    """The provider cannot save a card without a payment. Provider modules
    say so by leaving themselves out of the compatible providers of a
    validation."""
    provider_class = registry["payment.provider"]
    get_compatible = provider_class._get_compatible_providers

    def compatible(provider_self, *args, is_validation=False, **kwargs):
        providers = get_compatible(
            provider_self, *args, is_validation=is_validation, **kwargs
        )
        return providers - provider if is_validation else providers

    return patch.object(provider_class, "_get_compatible_providers", compatible)


def update_card_access_token(group):
    """The signed token of the update-card link of the emails."""
    query = parse_qs(urlsplit(group._my2_update_card_url()).query)
    return query["access_token"][0]


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

    def test_update_card_validation_needs_provider_support(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        group = contract.group_id
        provider = group.payment_mode_id.payment_provider_id
        nothing_due = invoice.browse()
        self.assertEqual(
            MyCompassionUpdateCard._update_card_provider(group, nothing_due), provider
        )
        with without_card_validation(self.registry, provider):
            # the payment of the arrears saves the card
            self.assertEqual(
                MyCompassionUpdateCard._update_card_provider(group, invoice), provider
            )
            # nothing due: no provider to save it with
            self.assertFalse(
                MyCompassionUpdateCard._update_card_provider(group, nothing_due)
            )
            invoice.invoice_date_due = fields.Date.today() + timedelta(days=10)
            transactions = self.env["payment.transaction"].search([])
            with (
                MockRequest(self.env),
                self.assertRaisesRegex(ValidationError, "only be saved with a payment"),
            ):
                MyCompassionUpdateCard().update_card_transaction(
                    group.id,
                    access_token=update_card_access_token(group),
                    provider_id=provider.id,
                    payment_method_id=self.env.ref("payment.payment_method_unknown").id,
                    token_id=None,
                    amount=None,
                    flow="direct",
                    tokenization_requested=True,
                    landing_route="/my2/update-card/done",
                    is_validation=True,
                )
            self.assertEqual(self.env["payment.transaction"].search([]), transactions)

    def _card(self, partner, provider, reference):
        return self.env["payment.token"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
                "partner_id": partner.id,
                "provider_ref": reference,
                "payment_details": "1111",
            }
        )

    def _update_card_transaction(self, group, invoice, partner, card):
        """A card update paying invoice, done with card."""
        _overrides, values = MyCompassionUpdateCard._update_card_tx_values(
            group, invoice
        )
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": card.provider_id.id,
                "payment_method_id": card.payment_method_id.id,
                "partner_id": partner.id,
                "reference": f"update-card-{card.provider_ref}",
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "operation": "online_direct",
                "token_id": card.id,
                **values,
            }
        )
        tx._set_done()
        return tx

    def assertStoredCard(self, group, card):
        """The card the database holds, not the cache."""
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(group.payment_token_id, card)

    def test_card_of_a_former_sponsor_never_replaces_the_card(self):
        # The group changed sponsor while the former one was changing its
        # card on the update-card page.
        contract, invoice, _token = self._make_chargeable_invoice()
        group = contract.group_id
        provider = group.payment_mode_id.payment_provider_id
        former_card = self._card(contract.partner_id, provider, "former-sponsor")
        tx = self._update_card_transaction(
            group, invoice, contract.partner_id, former_card
        )
        new_sponsor = self.env["res.partner"].create({"name": "New Sponsor"})
        new_card = self._card(new_sponsor, provider, "new-sponsor")
        group.write({"partner_id": new_sponsor.id, "payment_token_id": new_card.id})
        self.assertFalse(tx._my2_groups_taking_the_token())
        tx._my2_save_token_on_groups()
        self.assertStoredCard(group, new_card)

    def test_refused_card_leaves_the_card_unchanged(self):
        # A constraint refusing the new card after the field was written
        contract, invoice, token = self._make_chargeable_invoice()
        group = contract.group_id
        tx = self._update_card_transaction(
            group,
            invoice,
            contract.partner_id,
            token.copy({"provider_ref": "refused-card"}),
        )
        group_class = self.registry["recurring.contract.group"]
        write = group_class.write

        def write_then_refuse(groups, vals):
            res = write(groups, vals)
            if "payment_token_id" in vals:
                # pylint: disable=translation-required
                raise ValidationError("The card is refused.")
            return res

        with (
            patch.object(group_class, "write", write_then_refuse),
            self.assertLogs(
                "odoo.addons.my_compassion.models.payment_transaction", "ERROR"
            ),
        ):
            tx._my2_save_token_on_groups()
        self.assertStoredCard(group, token)

    def test_card_the_group_cannot_charge_is_not_taken(self):
        # From the update-card page, whose transaction may replace the card
        contract, _invoice, token = self._make_chargeable_invoice()
        group = contract.group_id
        providers = self._providers_the_group_cannot_charge_with(group)
        for reason, provider in providers.items():
            with self.subTest(provider=reason):
                card = self._card(contract.partner_id, provider, f"{reason}-card")
                tx = self.env["payment.transaction"].create(
                    {
                        "provider_id": provider.id,
                        "payment_method_id": card.payment_method_id.id,
                        "partner_id": contract.partner_id.id,
                        "reference": f"update-card-{reason}-provider",
                        "amount": 10.0,
                        "currency_id": provider.company_id.currency_id.id,
                        "operation": "online_direct",
                        "token_id": card.id,
                        "my2_card_update_group_id": group.id,
                    }
                )
                self.assertFalse(tx._my2_groups_taking_the_token())
                tx._my2_save_token_on_groups()
                self.assertStoredCard(group, token)


@tagged("post_install", "-at_install")
class TestUpdateCardPage(HttpCase, DigitalSeamCase):
    """The update-card page, opened from the link of an email."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The test client talks to 127.0.0.1: the MyCompassion website gets
        # that domain, like the sponsors' requests in production.
        cls.env.ref("my_compassion.my2_website").domain = cls.base_url()

    def _open_update_card_page(self, group):
        page = self.url_open(
            f"/my2/update-card?group_id={group.id}"
            f"&access_token={update_card_access_token(group)}"
        )
        self.assertEqual(page.status_code, 200)
        return " ".join(page.text.split())

    def _group_with_nothing_due(self):
        contract, invoice, _token = self._make_chargeable_invoice()
        invoice.invoice_date_due = fields.Date.today() + timedelta(days=10)
        return contract.group_id

    def test_page_checks_the_card_without_a_payment(self):
        # The provider is in test mode, unpublished: the sponsor of the
        # link is a public user, and still gets the provider of the group.
        group = self._group_with_nothing_due()
        self.assertFalse(group.payment_mode_id.payment_provider_id.is_published)
        page = self._open_update_card_page(group)
        self.assertIn("your new card will only be verified", page)
        self.assertNotIn("only be saved with a payment", page)

    def test_page_explains_a_card_needs_a_payment(self):
        group = self._group_with_nothing_due()
        with without_card_validation(
            self.registry, group.payment_mode_id.payment_provider_id
        ):
            page = self._open_update_card_page(group)
        self.assertIn("only be saved with a payment", page)
        self.assertNotIn("your new card will only be verified", page)
