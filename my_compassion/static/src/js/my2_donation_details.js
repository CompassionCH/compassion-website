document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.donation_details", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");

        publicWidget.registry.DonationDetails = publicWidget.Widget.extend({
            selector: ".my2_donation_details_form",

            events: {
                'change input[type="radio"][name="suggested_amount"]': "_onAmountChange",
            },

            /**
             * @override
             */
            start: function () {
                this.customAmountInput = this.$("#custom-amount");

                if (this.$("input[name='suggested_amount']:checked").val() !== "custom") {
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
        });

        return publicWidget.registry.DonationDetails;
    });
});
