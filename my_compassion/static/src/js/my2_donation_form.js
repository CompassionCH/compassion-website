odoo.define("my_compassion.donation_form", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    publicWidget.registry.DonationForm = publicWidget.Widget.extend({
        selector: ".my2_donation_form",

        events: {
            "change .suggested-amount": "_onAmountChange",
            "click .btn-submit": "_onSubmitClick",
        },

        /**
         * @override
         */
        start: function () {
            this.customAmountInput = this.$("#custom-amount");

            if (this.$(".suggested-amount:checked").val() !== "custom") {
                this.customAmountInput.hide();
            }
            this.customAmountInput.removeAttr("hidden");

            return this._super.apply(this, arguments);
        },

        /**
         * Handles the change event for the suggested amounts radio buttons.
         * @private
         * @param {Event} ev The jQuery event object.
         */
        _onAmountChange: function (ev) {
            if (this.$(ev.currentTarget).val() === "custom") {
                this.customAmountInput.slideDown("fast");
            } else {
                this.customAmountInput.slideUp("fast");
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

            // Trigger submission event
            this.$el.trigger(this.$(".btn-submit").data("submission-event"), [
                {
                    product_id: this.$("[name='product_id']").val(),
                    frequency: this.$(".donation-frequency input:checked").val(),
                    recipient: this.$("[name='recipient']").val(),
                    suggested_amount: this.$(".suggested-amount:checked").val(),
                    custom_amount: this.$("[name='custom_amount']").val(),
                },
            ]);
        },

        /**
         * Validates the payment form.
         * @returns {boolean} - True if valid, false otherwise.
         */
        _validateForm: function () {
            var isValid = true;

            // Remove previous error messages and styles
            this.$("input.is-invalid").removeClass("is-invalid");

            // Validate recipient
            if (this.$('select[name="recipient"]').find(":selected").val() === "") {
                isValid = false;
                this.$('select[name="recipient"]').addClass("is-invalid");
            }

            // Validate custom amount
            if (this.$(".suggested-amount:checked").val() == "custom") {
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

    return publicWidget.registry.DonationForm;
});
