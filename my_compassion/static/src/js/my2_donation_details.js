document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.donation_details", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.DonationDetails = publicWidget.Widget.extend({
            selector: ".my2_donation_details",

            events: {
                "donation-form:submit": "_onSubmit",
            },

            /**
             * @override
             */
            start: function () {
                return this._super.apply(this, arguments);
            },

            /**
             * Handles donation submission event.
             */
            _onSubmit: function (ev, data) {
                // Prevent double clicks
                this.$(".btn").prop("disabled", true);

                rpc.query({
                    route: "/my2/gifts/new",
                    params: data,
                })
                    .then(
                        function (data) {
                            // Redirect user to gift package page
                            window.location.href = "/my2/gift-package";
                        }.bind(this)
                    )
                    .guardedCatch(
                        function () {
                            // Re-enable buttons
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    );
            },
        });

        return publicWidget.registry.DonationDetails;
    });
});
