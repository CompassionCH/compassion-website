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
        email: {
            regex: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
            defaultErrorMessage: "Please enter a valid email address.",
        },
        phone: {
            regex: /^\+?(\d[\d\s-]{5,}\d)$/,
            defaultErrorMessage: "Please enter a valid phone number.",
        },
        required: {
            suffix: '<span class="text-mid-orange">*</span>',
            defaultErrorMessage: "This field is required.",
        },
    };

    publicWidget.registry.FormFieldValidator = publicWidget.Widget.extend({
        selector: ".form-field-component",
        events: {
            "blur input": "_onBlur",
            "change select": "_onBlur",
            "blur select": "_onBlur",
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
            this.validationType = this.$input.data("validate-type");

            if (this.isRequired) {
                this.$el.find("label").append(validationConfig.required.suffix);
            }

            if (validationConfig[this.validationType]) {
                this.config = validationConfig[this.validationType];
            }

            this.errorMessages = {
                required: this.$input.data("error-required") || validationConfig.required.defaultErrorMessage,
                format: this.$input.data("error-format") || this.config?.defaultErrorMessage,
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
            console.log("Validating field:", this.$input.attr("name"));
            this._clearError();
            var value = this.$input.val();

            if (this.isRequired && !value) {
                this._showError(this.errorMessages.required);
                return false;
            }

            if (this.validationType && value && this.config.regex) {
                if (!this.config.regex.test(value)) {
                    this._showError(this.errorMessages.format);
                    return false;
                }
            }

            return true;
        },

        /**
         * Displays an error message.
         */
        _showError: function (message) {
            this.$input.addClass("is-invalid");
            var $errorHint = $('<div class="input-invalid-hint text-mid-orange tiny-text mb-1">').text(message);

            var $selectContainer = this.$input.closest(".SelectComponent");
            if ($selectContainer.length > 0) {
                $selectContainer.before($errorHint);
            } else {
                this.$input.before($errorHint);
            }
        },

        /**
         * Removes existing error messages.
         */
        _clearError: function () {
            this.$el.find(".input-invalid-hint").remove();
            this.$input.removeClass("is-invalid");
        },
    });

    return publicWidget.registry.FormFieldValidator;
});
