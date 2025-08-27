document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.add_a_gift", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.AddAGift = publicWidget.Widget.extend({
            selector: ".my2-add-a-gift",

            events: {
                'change input[name="donation-type"]': "_onDonationTypeChange",
                "donation-form:submit": "_onDonationSubmit",
            },

            /**
             * @override
             */
            start: function () {
                this._onDonationTypeChange();
                return this._super.apply(this, arguments);
            },

            /**
             * Handles the change event for the donation type toggle buttons.
             * @private
             * @param {Event} ev
             */
            _onDonationTypeChange: function (ev) {
                const val = this.$('input[name="donation-type"]:checked').val();
                this.$(".product-tab").addClass("d-none");
                if (val === "gift") {
                    this.$("#gift-product-tab").removeClass("d-none");
                } else if (val === "fund") {
                    this.$("#fund-product-tab").removeClass("d-none");
                }
            },

            /**
             * Handles donation submission event.
             */
            _onDonationSubmit: function (ev, data) {
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

        return publicWidget.registry.AddAGift;
    });
});
