from odoo.addons.my_compassion.tests.common import DigitalSeamCase


class PayuDigitalCase(DigitalSeamCase):
    def _make_payu_chargeable_invoice(self):
        """A due invoice of a digital contract whose group pays with a card
        saved at PayU. Returns (contract, invoice, token)."""
        contract, invoice, token = self._make_chargeable_invoice()
        token.provider_id.write(
            {
                "code": "payu_gpo",
                "allow_tokenization": True,
                "payu_gpo_pos_id": "300746",
                "payu_gpo_client_id": "300746",
                "payu_gpo_client_secret": "test-client-secret",
                "payu_gpo_second_key": "test-second-key",
            }
        )
        return contract, invoice, token
