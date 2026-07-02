/** @odoo-module **/

/**
 * Form Field Validator Widget
 *
 * publicWidget mounted on `.form-field-component` wrappers. Validates input
 * and select values on blur/change and renders inline error hints.
 *
 * Validation rules (declared via `data-validateType` on the input/select):
 *   - required: enforced from the HTML `required` attribute; appends an
 *     asterisk span to the label and blocks submission on empty value.
 *   - email: RFC-style address pattern.
 *   - phone: international phone number (leading +, 7-17 digits/spaces/hyphens).
 *   - name: unicode letters, space, dot, apostrophe, hyphen; 2-50 characters.
 *   - zip: postal codes starting with at most 2 letters; max 15 characters.
 *
 * Error message overrides: `data-errorRequired` and `data-errorFormat` on the
 * input element take precedence over the built-in defaults.
 *
 * DOM contract:
 *   - Adds `is-invalid` to the input/select on failure; removes it on clear.
 *   - Appends `<div class="input-invalid-hint ...">` after the input (or after
 *     its `.SelectComponent` ancestor when present).
 *   - Color class is `text-pure-white` when the input carries `dark-bg`,
 *     otherwise `text-mid-orange`.
 *   - Required labels receive `<span class="text-mid-orange required-asterisk">*</span>`.
 *
 * Public API:
 *   - `validate()`: triggers full validation and returns true/false; safe to
 *     call from parent form code at submission time.
 */

import publicWidget from "@web/legacy/js/public/public_widget";

const validationConfig = {
  required: {
    suffix: '<span class="text-mid-orange required-asterisk">*</span>',
    defaultErrorMessage: "This field is required.",
  },
  email: {
    regex: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    defaultErrorMessage: "Please enter a valid email address.",
  },
  phone: {
    regex: /^\+?(\d[\d\s-]{5,15}\d)$/,
    defaultErrorMessage: "Please enter a valid phone number.",
  },
  name: {
    // Allow international letters, space, dot, apostrophe, hyphen.
    // Length: 2 to 50 characters.
    regex: /^[\p{L} .'-]{2,50}$/u,
    defaultErrorMessage: "Please enter a valid name (2-50 characters, no numbers).",
  },
  zip: {
    // Allow ZIP codes to start with at most 2 letters, max 15 characters.
    // Allowed 4802 (CH), 10115 (DE, FR, IT), SW1A 1AA (UK)
    // Not allowed: rhiq9rq4q4, DEC1234
    regex: /^([0-9]|[a-zA-Z]{1,2}[0-9\s-])[a-zA-Z0-9\s-]{1,14}$/,
    defaultErrorMessage:
      "Please enter a valid ZIP/Postal code. (enter 0000 if not applicable)",
  },
  number: {
    // Strictly positive numbers, integer or decimal (1, 2.5, .5; not 0 or -3).
    regex: /(^[1-9]\d*(\.\d+)?$)|(^0?\.\d*[1-9]\d*$)/,
    defaultErrorMessage: "Please enter a valid number.",
  },
};

publicWidget.registry.themeCompassionFormFieldValidator = publicWidget.Widget.extend({
  selector: ".form-field-component",
  events: {
    "blur input": "_onBlur",
    "change select": "_onBlur",
  },

  init: function () {
    this._super.apply(this, arguments);
    this.validationType = null;
    this.config = {};
  },

  /**
   * Called after the widget's DOM element is available. Reads validation
   * configuration from data attributes and appends the required asterisk
   * to labels when the field is marked required.
   */
  start: function () {
    this._super.apply(this, arguments);
    this.$el.data("widget", this);

    this.$input = this.$("input, select");
    this.isRequired = this.$input.prop("required");
    this.validationType = this.$input.data("validateType");

    if (this.isRequired) {
      this.$el.find("label").append(validationConfig.required.suffix);
    }

    if (validationConfig[this.validationType]) {
      this.config = validationConfig[this.validationType];
    }

    this.errorMessages = {
      required:
        this.$input.data("errorRequired") ||
        validationConfig.required.defaultErrorMessage,
      format:
        this.$input.data("errorFormat") ||
        (this.config && this.config.defaultErrorMessage),
    };
  },

  /**
   * Validates the field when it loses focus or when a select changes.
   */
  _onBlur: function () {
    this.validate();
  },

  /**
   * Runs validation for this field. May also be called externally by a
   * parent form at submission time.
   * @returns {Boolean} true when the field value passes all applicable rules.
   */
  validate: function () {
    this.clearError();
    const value = this.$input.val();

    if (this.isRequired && !value) {
      this.showError(this.errorMessages.required);
      return false;
    }

    if (this.validationType && value && this.config.regex) {
      if (!this.config.regex.test(value)) {
        this.showError(this.errorMessages.format);
        return false;
      }
    }

    return true;
  },

  /**
   * Removes any existing error hint and the is-invalid marker from the input.
   */
  clearError: function () {
    this.$el.find(".input-invalid-hint").remove();
    this.$input.removeClass("is-invalid");
  },

  /**
   * Marks the input as invalid and inserts the error hint into the DOM.
   * Placement: after the input element, or after its `.SelectComponent`
   * ancestor when one is present. Color adapts to the background context.
   */
  showError: function (message) {
    this.$input.addClass("is-invalid");

    const isDark = this.$input.hasClass("dark-bg");
    const colorClass = isDark ? "text-pure-white" : "text-mid-orange";
    const classes = `input-invalid-hint ${colorClass} tiny-text mt-2`;

    const $errorHint = $(`<div class="${classes}">`).text(message);

    const $selectContainer = this.$input.closest(".SelectComponent");
    if ($selectContainer.length > 0) {
      $selectContainer.after($errorHint);
    } else {
      this.$input.after($errorHint);
    }
  },
});

export default publicWidget.registry.themeCompassionFormFieldValidator;
