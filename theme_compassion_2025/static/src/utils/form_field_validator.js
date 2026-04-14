/*
 * Form Field Validator Widget
 *
 * Provides client-side validation for form fields inside
 * `.form-field-component` wrappers. It validates:
 *   - required fields
 *   - email format
 *   - phone number format
 *
 * Features:
 *   - Displays inline error messages below/above inputs
 *   - Marks invalid fields with the `is-invalid` class
 *   - Appends an asterisk (*) to required field labels
 *
 *
 * -------------------------------------------------------------------------------
 */
odoo.define("my_compassion.form_field_validator", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");

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
            defaultErrorMessage: "Please enter a valid ZIP/Postal code. (enter 0000 if not applicable)",
        },
    };

    publicWidget.registry.FormFieldValidator = publicWidget.Widget.extend({
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
         * The start method is called after the widget's DOM element
         * has been rendered and is available. This is the right place for DOM manipulations.
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
                required: this.$input.data("errorRequired") || validationConfig.required.defaultErrorMessage,
                format: this.$input.data("errorFormat") || (this.config && this.config.defaultErrorMessage),
            };
        },

        /**
         * Validates the field when it loses focus.
         */
        _onBlur: function () {
            this.validate();
        },

        /**
         * The central validation function. Can also be called externally.
         * @returns {Boolean}
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
         * Removes existing error messages.
         */
        clearError: function () {
            this.$el.find(".input-invalid-hint").remove();
            this.$input.removeClass("is-invalid");
        },
        /**
         * Displays an error message.
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

    return publicWidget.registry.FormFieldValidator;
});
