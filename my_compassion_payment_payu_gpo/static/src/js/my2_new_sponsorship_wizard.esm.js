/** @odoo-module **/

import {NewSponsorshipWizard} from "@my_compassion/js/my2_new_sponsorship_wizard";

NewSponsorshipWizard.include({
  /**
   * The names on the card are required only by the PayU buttons: the other
   * payment modes of the page (e.g. a standing order) take no card.
   *
   * @override
   */
  _onStepClick(ev) {
    const isRequired = Boolean($(ev.currentTarget).data("payu-gpo"));
    this.$(
      'input[name="cardholder_firstname"], input[name="cardholder_lastname"]'
    ).each((i, input) => {
      const field = $(input).closest(".form-field-component").data("widget");
      if (field) {
        field.isRequired = isRequired;
        field.clearError();
      }
    });
    return this._super(...arguments);
  },
});
