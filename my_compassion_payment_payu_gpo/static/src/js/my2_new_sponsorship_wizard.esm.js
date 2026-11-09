/** @odoo-module **/

import {NewSponsorshipWizard} from "@my_compassion/js/my2_new_sponsorship_wizard";

NewSponsorshipWizard.include({
  // The PayU radios' data-payu-gpo is mirrored on the Continue button with
  // the payment mode, so the click below reads it there.
  paymentModeDataKeys: [
    ...NewSponsorshipWizard.prototype.paymentModeDataKeys,
    "payu-gpo",
  ],

  /**
   * The names on the card are required only when a PayU payment mode is the
   * checked one: the other payment modes of the page (e.g. a standing
   * order) take no card.
   *
   * @override
   */
  _onStepClick(ev) {
    const isRequired = Boolean($(ev.currentTarget).data("payu-gpo"));
    this.$(
      'input[name="cardholder_firstname"], input[name="cardholder_lastname"]'
    ).each((i, input) => {
      // The page is submitted by script, without the browser's checks:
      // spaces are no name, the widget's own check then sees it empty.
      input.value = input.value.trim();
      const field = $(input).closest(".form-field-component").data("widget");
      if (field) {
        field.isRequired = isRequired;
        field.clearError();
      }
    });
    return this._super(...arguments);
  },
});
