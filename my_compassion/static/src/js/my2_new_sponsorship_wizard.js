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
    "change #birthdate": "_onBirthDateChange",
  },

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
   * Updates UI
   * @private
   * @param speed
   */
  _updateUI: function (speed = 0) {
    if (this.$(".wap-contribute:checked").val() === "true") {
      this.$("#wap-contribution-amount").slideDown(speed);
    } else {
      this.$("#wap-contribution-amount").slideUp(speed);
    }

    if (this.$(".suggested-amount:checked").val() === "custom") {
      this.$(".custom-amount-field").slideDown(speed);
    } else {
      this.$(".custom-amount-field").slideUp(speed);
    }
  },

  /**
   * Checks the age immediately when the user inputs their birthdate.
   * @param {Event} ev
   */
  _onBirthDateChange: function (ev) {
    const sponsorship_type = this.$(".btn-next:not(#wap-age-modal .btn-next)").data(
      "sponsorship-type"
    );

    if (sponsorship_type === "write_and_pray") {
      this._checkWAPAge();
    }
  },

  /**
   * Evaluates if the birthdate qualifies for Write & Pray.
   * @returns {Boolean} - true if valid, false if too old.
   */
  _checkWAPAge: function () {
    const birthdateVal = this.$('input[name="birthdate"]').val();
    if (!birthdateVal) return true; // Skip if no date is entered yet

    const dateThreshold = new Date();
    dateThreshold.setFullYear(dateThreshold.getFullYear() - 25);
    const birthdate = new Date(birthdateVal);

    if (birthdate < dateThreshold) {
      Modal.getOrCreateInstance(this.el.querySelector("#wap-age-modal")).show();
      return false;
    }
    return true;
  },
});

publicWidget.registry.NewSponsorshipWizard = NewSponsorshipWizard;
