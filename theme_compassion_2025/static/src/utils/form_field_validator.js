odoo.define("my_compassion.form_field_validator", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");
    console.log("RangeInput component loaded");

    publicWidget.registry.FormFieldValidator = publicWidget.Widget.extend({
        selector: ".form-field-component",
        events: {
            "blur input, input select": "_onBlur",
        },

        init: function () {
            this._super.apply(this, arguments);
        },

        /**
         * Die start-Methode wird aufgerufen, nachdem das DOM-Element des Widgets
         * gerendert und verfügbar ist. Dies ist der richtige Ort für DOM-Manipulationen.
         */
        start: function () {
            this._super.apply(this, arguments);
            this.$input = this.$("input, select");
            this.validationType = this.$input.data("validate-type");

            this.errorMessages = {
                required: this.$input.data("error-required") || "This field is required.",
                format: this.$input.data("error-format") || "Invalid format.",
            };

            this.regex = {
                email: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
                phone: /^\+?(\d[\d\s-]{5,}\d)$/,
            };
        },
        /**
         * Validiert das Feld, wenn der Fokus verlassen wird.
         */
        _onBlur: function () {
            this.validate();
        },

        /**
         * Die zentrale Validierungsfunktion. Kann auch von aussen aufgerufen werden.
         * @returns {boolean}
         */
        validate: function () {
            this._clearError();
            var value = this.$input.val();

            // 1. Required-Prüfung
            if (this.$input.prop("required") && !value) {
                this._showError(this.errorMessages.required);
                return false;
            }

            // 2. Format-Prüfung (nur wenn ein Wert vorhanden ist)
            if (this.validationType && value && this.regex[this.validationType]) {
                if (!this.regex[this.validationType].test(value)) {
                    this._showError(this.errorMessages.format);
                    return false;
                }
            }

            this.$input.removeClass("is-invalid");
            return true;
        },

        /**
         * Zeigt eine Fehlermeldung an.
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
         * Entfernt bestehende Fehlermeldungen.
         */
        _clearError: function () {
            this.$el.find(".input-invalid-hint").remove();
            this.$input.removeClass("is-invalid");
        },
    });

    return publicWidget.registry.FormFieldValidator;
});