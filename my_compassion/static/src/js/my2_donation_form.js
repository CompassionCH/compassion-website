/** @odoo-module **/

/**
 * Donation form hub.
 *
 * Drives the amount/recipient selection of a donation form
 * (`.my2_donation_form`): keeps the suggested-amount radios and the custom
 * amount input in sync, fetches the donation limits of the selected
 * recipient (`/my2/gifts/get-limits`) and validates the form. On a valid
 * submission it triggers the event named by the submit button's
 * `data-submission-event` attribute with the donation payload; the page
 * widget hosting the form (donation details, add-a-gift, gift package)
 * listens to that event and persists the donation.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

export const DonationForm = publicWidget.Widget.extend({
  selector: ".my2_donation_form",

  events: {
    "change .suggested-amount": "_onAmountChange",
    "change .SelectComponent": "_onRecipientChange",
    "click .btn-submit": "_onSubmitClick",
    "click .limits-toggle": "_onLimitsToggleClick",
    "click #custom-amount": "_onCustomAmountFocus",
    "focus #custom-amount": "_onCustomAmountFocus",
  },

  /**
   * @override
   */
  start: function () {
    this.edit_mode = this.$el.data("edit-mode");
    this.customAmountInput = this.$("#custom-amount");
    this.customAmountInput.removeAttr("hidden");

    this.$(".limits-info").hide();
    this.$(".limits-info").removeAttr("hidden");

    this._onRecipientChange();

    return this._super.apply(this, arguments);
  },

  /**
   * Handles the change event for the suggested amounts radio buttons.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onAmountChange: function (ev) {
    // If the user selects a preset (Low/Med/High), we just clear the custom input visual state.
    if (this.$(ev.currentTarget).val() !== "custom") {
      this.customAmountInput.val("");
      this.customAmountInput.removeClass("is-invalid");
    }
  },

  /**
   * Helper to automatically select the 'custom' radio button when the user
   * interacts with the text input.
   * @private
   */
  _onCustomAmountFocus: function () {
    var $customRadio = this.$(".suggested-amount[value='custom']");
    if (!$customRadio.prop("checked")) {
      $customRadio.prop("checked", true).trigger("change");
    }
  },

  /**
   * Handles the change event for the recipient select.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onRecipientChange: function (ev) {
    const $recipient_select = this.$("[name='recipient']");
    if ($recipient_select.length === 0) {
      return;
    }
    if (this.edit_mode) {
      this.$(".amount-selection").removeAttr("hidden");
    } else if ($recipient_select.val()) {
      this.$(".btn").prop("disabled", true);
      $recipient_select.prop("disabled", true);

      rpc("/my2/gifts/get-limits", {
        product_id: this.$("[name='product_id']").val(),
        sponsorship_id: $recipient_select.val(),
      })
        .then(
          function (data) {
            this.$(".btn").prop("disabled", false);
            $recipient_select.prop("disabled", false);
            this.$(".donation-request-error").attr("hidden", true);

            if (data.remaining_donations !== null && data.remaining_donations <= 0) {
              this.$(".limit-reached-message").removeAttr("hidden");
              this.$(".amount-selection").attr("hidden", true);
            } else {
              this.$(".amount-selection").removeAttr("hidden");
              this.$(".limit-reached-message").attr("hidden", true);
            }
          }.bind(this)
        )
        .catch(
          function () {
            this.$(".btn").prop("disabled", false);
            $recipient_select.prop("disabled", false);
            this.$(".donation-request-error").removeAttr("hidden");
          }.bind(this)
        );
    } else {
      this.$(".amount-selection").attr("hidden", true);
      this.$(".limit-reached-message").attr("hidden", true);
    }
  },

  /**
   * Handles click events on the "Add & check out" button.
   * @param {Event} ev
   */
  _onSubmitClick: function (ev) {
    // Prevent double clicks
    this.$(".btn").prop("disabled", true);

    // Validate the form
    if (!this._validateForm()) {
      this.$(".btn").prop("disabled", false);
      return; // Stop execution if validation fails
    }

    const sponsorship_id = this.$("[name='recipient']").val();
    const product_id = this.$("[name='product_id']").val();

    rpc("/my2/gifts/get-limits", {
      product_id: product_id,
      sponsorship_id: sponsorship_id,
    })
      .then(
        function (data) {
          this.$(".btn").prop("disabled", false);
          this.$(".donation-request-error").attr("hidden", true);

          // Compute amount
          const suggested_amount = this.$(".suggested-amount:checked").val();
          const custom_amount = this.$("[name='custom_amount']").val();
          let amount = suggested_amount;
          if (amount === "custom") {
            amount = custom_amount;
          }

          if (
            (data.min_amount !== null && amount < data.min_amount) ||
            (data.max_amount !== null && amount > data.max_amount) ||
            (data.remaining_donations !== null &&
              data.remaining_donations <= 0 &&
              !this.edit_mode)
          ) {
            this.$(".limit-error-message").removeAttr("hidden");
            return;
          }
          this.$(".limit-error-message").attr("hidden", true);

          // Trigger submission event
          this.$el.trigger(this.$(".btn-submit").data("submission-event"), [
            {
              product_id: product_id,
              frequency:
                this.$(".donation-frequency input:checked").val() || "one_time",
              recipient: sponsorship_id,
              suggested_amount: suggested_amount,
              custom_amount: custom_amount,
            },
          ]);
        }.bind(this)
      )
      .catch(
        function () {
          this.$(".btn").prop("disabled", false);
          this.$(".donation-request-error").removeAttr("hidden");
        }.bind(this)
      );
  },

  /**
   * Handles click events on the donation limits toggle.
   * @param {Event} ev
   */
  _onLimitsToggleClick: function (ev) {
    this.$(".limits-info").slideToggle("fast");
  },

  /**
   * Validates the payment form.
   * @returns {Boolean} - True if valid, false otherwise.
   */
  _validateForm: function () {
    let isValid = true;

    // Remove previous error messages and styles
    this.$("input.is-invalid").removeClass("is-invalid");

    // Validate recipient
    const $recipient = this.$('select[name="recipient"]');
    if ($recipient.length && $recipient.find(":selected").val() === "") {
      isValid = false;
      this.$('select[name="recipient"]').addClass("is-invalid");
    }

    // Validate custom amount
    if (this.$(".suggested-amount:checked").val() === "custom") {
      const $input = this.$("#custom-amount");
      const custom_amount = Number($input.val());

      // Check if the result is a finite number AND is greater than 0.
      // Number.isFinite() correctly handles NaN, Infinity, and -Infinity.
      if (!(Number.isFinite(custom_amount) && custom_amount > 0)) {
        isValid = false;
        $input.addClass("is-invalid");
      }
    }

    return isValid;
  },
});

publicWidget.registry.DonationForm = DonationForm;
