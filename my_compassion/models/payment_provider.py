import json

from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    def _stripe_get_inline_form_values(
        self, amount, currency, partner_id, is_validation, payment_method_sudo=None,
        **kwargs,
    ):
        """Never offer Stripe a placeholder as the payer's name.

        Core fills the Payment Element's defaultValues.billingDetails from
        partner.name, and a fast-checkout sponsor's partner carries the
        MY2_PLACEHOLDER_NAME placeholder until they say who they are. Left
        alone, Stripe takes "(pending)" as the cardholder name, reports it
        back on payment_intent.succeeded, and the capture path writes it over
        the placeholder it came from - clearing my2_name_placeholder, which
        is what _my2_details_pending keys on, so the details form stops
        rendering and the sponsor is never asked at all.

        Blanking it instead leaves the Element's name field empty, so the
        sponsor fills it in once, in Stripe's own form. The field's
        visibility is Stripe's to decide (fields.billingDetails.name defaults
        to 'auto' and has no 'always'), so an empty name is still a possible
        outcome - which is why the details form keeps asking for the name
        whenever no usable one arrived.
        """
        values = super()._stripe_get_inline_form_values(
            amount,
            currency,
            partner_id,
            is_validation,
            payment_method_sudo=payment_method_sudo,
            **kwargs,
        )
        partner = self.env["res.partner"].sudo().browse(partner_id).exists()
        if not partner.my2_name_placeholder:
            return values
        parsed = json.loads(values)
        parsed.get("billing_details", {})["name"] = ""
        return json.dumps(parsed)

    def _is_tokenization_required(self, my2_sponsorship=False, **kwargs):
        """Sponsorship first payments must save the instrument: the monthly
        off-session charge has nothing to charge without a token.

        The flag arrives as a kwarg when the transaction is created and as
        a context key when the payment form is rendered. The provider's own
        inline form template calls this method with its fixed kwargs and
        feeds the answer to its payment widget, so only the environment can
        carry the flag at render time.
        """
        return bool(
            my2_sponsorship
            or self.env.context.get("my2_sponsorship")
            or super()._is_tokenization_required(**kwargs)
        )
