/** @odoo-module **/

/*
 * Handle the new sponsorship wizard. It handles users actions such as
 * step navigation (next/previous), form validation, dynamic content
 * loading, and communication with the server via API calls to process the
 * sponsorship application.
 *
 * Used in /templates/pages/my2_new_sponsorship_wizard.xml
 * ------------------------------------------------------------------------------- */

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

export const NewSponsorshipWizard = publicWidget.Widget.extend({
  selector: ".new-sponsorship-wizard-form",
  events: {
    "click .btn-next, .btn-previous": "_onStepClick",
    "click .btn-sponsor": "_onSponsorClick",
    "change .wap-contribute": "_onWAPContributeChange",
    "change .suggested-amount": "_onAmountChange",
    "input input[name=custom_amount]": "_onCustomAmountInput",
    "change #birthdate": "_onBirthDateChange",
    "change .payment-method-radio": "_onPaymentModeRadioChange",
    "change input[name=sponsorship_plus]": "_onSponsorshipPlusChange",
  },

  /**
   * The data-* keys of the checked payment-mode radio that the step's
   * Continue button mirrors (see _onPaymentModeRadioChange). Modules that
   * read more keys off the clicked button add them here.
   */
  paymentModeDataKeys: ["payment-mode", "payment-code"],

  /**
   * @override
   */
  start: function () {
    this._super.apply(this, arguments);

    this._updateUI();
  },

  /**
   * Handles the click on "Next" or "Previous" buttons.
   * @param {Event} ev
   */
  _onStepClick: function (ev) {
    ev.preventDefault();

    const action = $(ev.currentTarget).data("action"); // 'next', 'previous'
    const sponsorship_type = $(ev.currentTarget).data("sponsorship-type"); // 'standard', 'write_and_pray'

    // Don't validate when moving backwards
    if (action !== "previous" && !this._validateForm()) {
      return; // Stop execution if validation fails
    }

    // Check age for Write&Pray
    if (action !== "previous" && sponsorship_type === "write_and_pray") {
      if (!this._checkWAPAge()) {
        return; // Stop execution if age check fails
      }
    }

    // Prevent double clicks
    this.$(".btn").prop("disabled", true);

    // Serialize form and add action
    const formData = this.$el.serializeArray();
    formData.push({name: "action", value: action});
    formData.push({name: "sponsorship_type", value: sponsorship_type});

    // The fast-checkout page offers one button per payment mode instead of a
    // dropdown: the mode of the button that was pressed is the choice. Sent
    // the same way as the action above, so a mode button goes through the
    // one step call every other button already uses.
    const payment_mode = $(ev.currentTarget).data("payment-mode");
    if (payment_mode) {
      formData.push({name: "payment_method", value: payment_mode});
    }

    // Use RPC to call the controller method
    rpc("/my2/new-sponsorship/step", this._serializeForm(formData))
      .then(
        function (data) {
          // Replace the form's inner content with the new step's HTML
          if (data.html) {
            // The step's HTML swap removes the modal element, so any open
            // backdrop is cleared manually before replacing the content.
            document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
            document.body.classList.remove("modal-open");

            this.$(".new-sponsorship-wizard-form-content").html(data.html);
            $("html, body").animate({scrollTop: 0}, "slow");
          }
          if (data.finish) {
            this.$el.submit();
          } else {
            // Re-enable buttons
            this.$(".btn").prop("disabled", false);
            this._updateUI();
          }
        }.bind(this)
      )
      .catch(
        function () {
          // Re-enable buttons also in case of error
          this.$(".btn").prop("disabled", false);
        }.bind(this)
      );
  },

  /**
   * Validates required fields in the current step.
   * @returns {Boolean} - True if valid, false otherwise.
   */
  _validateForm: function () {
    var isValid = true;

    this.$(".form-field-component:visible").each(function () {
      var fieldWidget = $(this).data("widget");

      if (fieldWidget && !fieldWidget.validate()) {
        isValid = false;
      }
    });

    // The fast checkout's payment-mode radios have no default: one must be
    // picked before the step is submitted.
    const $paymentModes = this.$(".payment-method-radio");
    if ($paymentModes.length && !$paymentModes.filter(":checked").length) {
      this.$(".ns-payment-mode-error").removeClass("d-none");
      isValid = false;
    }

    return isValid;
  },

  /**
   * Helper to convert form data array to a key-value object.
   * @param {Array} formData
   * @returns {Object}
   */
  _serializeForm: function (formData) {
    const obj = {};
    for (const field of formData) {
      obj[field.name] = field.value;
    }
    return obj;
  },

  /**
   * Handles the change event for the Write&Pray contribute radio buttons.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onWAPContributeChange: function (ev) {
    this._updateUI("fast");
  },

  /**
   * Handles the change event for the suggested amounts radio buttons.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onAmountChange: function (ev) {
    this._updateUI("fast");
  },

  /**
   * Handles typing in the custom amount field: there is no separate
   * "Custom amount" toggle any more, so typing here is itself what
   * selects the custom amount over a suggested one.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onCustomAmountInput: function (ev) {
    this.$("#suggested-custom").prop("checked", true);
    this._updateUI("fast");
  },

  /**
   * Updates UI
   * @private
   * @param speed
   */
  _updateUI: function (speed = 0) {
    const contributing = this.$(".wap-contribute:checked").val() === "true";

    if (contributing) {
      this.$("#wap-contribution-amount").slideDown(speed);
    } else {
      this.$("#wap-contribution-amount").slideUp(speed);
    }

    this._updateWAPPrice(contributing);
  },

  /**
   * Reflects the "which describes you" choice (and, once contributing,
   * the picked amount) on the child card's price, the same figure
   * finish_sponsorship names on the contract line - "No payment" for the
   * free-godparent branch, since a Write&Pray sponsorship is never
   * collected either way.
   * @param {Boolean} contributing
   * @private
   */
  _updateWAPPrice: function (contributing) {
    const $price = this.$("#wap-child-price");
    if (!$price.length) {
      return; // Not the Write&Pray fast-checkout step.
    }

    if (!contributing) {
      $price.text("No payment");
      return;
    }

    let amount = this.$(".suggested-amount:checked").val();
    if (amount === "custom") {
      amount = this.$('input[name="custom_amount"]').val();
    }
    amount = parseFloat(amount);
    if (!amount) {
      $price.text("No payment");
      return;
    }
    $price.text(`${$price.data("currencyName")} ${amount}.-`);
  },

  /**
   * The fast checkout renders one radio per payment mode in the step's own
   * left column, with a single Continue button doing the actual submit.
   * That button carries no payment mode of its own, so the checked radio's
   * paymentModeDataKeys are copied onto it here - as attributes and as
   * jQuery data, since jQuery caches a .data() read and would otherwise keep
   * returning the mode of an earlier click. This is what lets a click
   * handler such as the my_compassion_switzerland eBill one keep reading
   * the mode off the clicked button without knowing radios are involved.
   * A key the checked radio does not carry is removed from the button.
   * @param {Event} ev
   */
  _onPaymentModeRadioChange: function (ev) {
    const $radio = $(ev.currentTarget);
    const $button = this.$(".btn-next");
    for (const key of this.paymentModeDataKeys) {
      if ($radio.attr(`data-${key}`) === undefined) {
        $button.removeAttr(`data-${key}`).removeData(key);
      } else {
        $button.attr(`data-${key}`, $radio.attr(`data-${key}`));
        $button.data(key, $radio.data(key));
      }
    }
    this.$(".ns-payment-mode-error").addClass("d-none");
  },

  /**
   * Keeps the fast checkout's right-column "Total" live as Sponsorship Plus
   * is chosen, off the total element's own data-base-amount/data-plus-amount
   * (server-rendered once, from the same amounts the donation card and the
   * Sponsorship Plus choice already show) rather than round-tripping a step
   * call. The choice is any input named sponsorship_plus: the base
   * checkbox, or radios a country module puts in its place, where the value
   * "0" means without Plus. Nothing checked shows the base amount. Only the
   * amount is rewritten: the translated "/mo." after it is the template's.
   */
  _onSponsorshipPlusChange: function () {
    const $total = this.$("#ns-total-amount");
    if (!$total.length) {
      return;
    }
    const base = parseFloat($total.data("baseAmount")) || 0;
    const plus = parseFloat($total.data("plusAmount")) || 0;
    const $choice = this.$("input[name=sponsorship_plus]:checked");
    const withPlus = $choice.length > 0 && $choice.val() !== "0";
    const total = base + (withPlus ? plus : 0);
    const formatted = total % 1 === 0 ? `${total}.-` : total.toFixed(2);
    $total.text(`${$total.data("currencyName")}\u00a0${formatted}`);
  },

  /**
   * Checks the age immediately when the user inputs their birthdate.
   * @param {Event} ev
   */
  _onBirthDateChange: function (ev) {
    const sponsorship_type = this.$(".btn-next").data("sponsorship-type");

    if (sponsorship_type === "write_and_pray") {
      this._checkWAPAge();
    }
  },

  /**
   * Evaluates if the birthdate qualifies for Write & Pray. Too old sends
   * the visitor straight to the standard flow for the same child - not a
   * modal offering to switch, since there is nothing left to do on this
   * page once they are ineligible. wap_ineligible=1 is what makes the
   * standard fast-checkout page explain why they landed there instead of
   * where they clicked.
   * @returns {Boolean} - true if valid, false if too old (about to redirect).
   */
  _checkWAPAge: function () {
    const birthdateVal = this.$('input[name="birthdate"]').val();
    if (!birthdateVal) return true; // Skip if no date is entered yet

    const dateThreshold = new Date();
    dateThreshold.setFullYear(dateThreshold.getFullYear() - 25);
    const birthdate = new Date(birthdateVal);

    if (birthdate < dateThreshold) {
      window.location.href = `${window.location.pathname}?sponsorship_type=standard&wap_ineligible=1`;
      return false;
    }
    return true;
  },
});

publicWidget.registry.NewSponsorshipWizard = NewSponsorshipWizard;
