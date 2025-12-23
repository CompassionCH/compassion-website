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

    var publicWidget = require("web.public.widget");

    var validationConfig = {
        required: {
            suffix: '<span class="text-mid-orange">*</span>',
            defaultErrorMessage: "This field is required.",
        },
        email: {
            regex: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
            defaultErrorMessage: "Please enter a valid email address.",
        },
        phone: {
            regex: /^\+?(\d[\d\s-]{5,}\d)$/,
            defaultErrorMessage: "Please enter a valid phone number.",
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
                format: this.$input.data("errorFormat") || this.config?.defaultErrorMessage,
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
         * @returns {boolean}
         */
        validate: function () {
            this.clearError();
            var value = this.$input.val();

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
            var $errorHint = $('<div class="input-invalid-hint text-mid-orange tiny-text mt-2">').text(message);

            var $selectContainer = this.$input.closest(".SelectComponent");
            if ($selectContainer.length > 0) {
                $selectContainer.after($errorHint);
            } else {
                this.$input.after($errorHint);
            }
        },
    });

    return publicWidget.registry.FormFieldValidator;
});
