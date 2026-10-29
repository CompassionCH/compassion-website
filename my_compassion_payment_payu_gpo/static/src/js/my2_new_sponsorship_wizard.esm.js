/** @odoo-module **/

import {NewSponsorshipWizard} from "@my_compassion/js/my2_new_sponsorship_wizard";

NewSponsorshipWizard.include({
    /**
     * The name on the card is required only by the PayU buttons: the other
     * payment modes of the page (e.g. a standing order) take no card.
     *
     * @override
     */
    _onStepClick(ev) {
        const field = this.$('input[name="cardholder_name"]')
            .closest(".form-field-component")
            .data("widget");
        if (field) {
            field.isRequired = Boolean($(ev.currentTarget).data("payu-gpo"));
            field.clearError();
        }
        return this._super(...arguments);
    },
});
