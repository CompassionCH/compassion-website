odoo.define("website_event_compassion.donation_form", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");

    publicWidget.registry.EventDonationForm = publicWidget.Widget.extend({
        selector: "#event_donation_form",

        events: {
            "click .amount_button": "onAmountButtonClick",
            "change #amount_custom_input": "onAmountCustomInputChange",
            "submit form": "onFormSubmit",
        },

        onAmountButtonClick: function (el) {
            const $button = $(el.currentTarget);
            $(".amount_button").removeClass("active");
            $button.addClass("active");
            $("#amount_custom_input").val("");
            $("#input_amount").val($button.data("donation-value"));
        },
        onAmountCustomInputChange: function (el) {
            $(".amount_button").removeClass("active");
            $("#input_amount").val($(el.currentTarget).val());
        },
        onFormSubmit: function (el) {
            if (!$("#input_amount").val()) {
                el.preventDefault();
                $(".error").hide().removeClass("d-none").fadeIn();
            }
        },
    });
});
