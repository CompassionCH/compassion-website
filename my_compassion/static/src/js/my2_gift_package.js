document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.gift_package", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.GiftPackage = publicWidget.Widget.extend({
            selector: ".my2_gift_package_form",

            events: {
                'donation-item:delete': "_onDonationItemDelete",
            },

            /**
             * @override
             */
            start: function () {
                return this._super.apply(this, arguments);
            },

            /**
             * Handles donation item delete events.
             * @private
             * @param {Event} ev The jQuery event object.
             */
            _onDonationItemDelete: function (ev) {
                const order_line_id = ev.detail.order_line_id;

                // Disable buttons and apply deleting style
                this.$(".btn").prop("disabled", true);
                this.$(".donation-item-" + order_line_id).addClass("deleting");

                rpc.query({
                    route: "/my2/gift-package/delete-item",
                    params: {
                        order_line_id: order_line_id,
                    },
                })
                .then(
                    function (data) {
                        // Replace the form's inner content with the new step's HTML
                        if (data.html) {
                            $("#gift-package-content-wrapper").html(data.html);
                        }
                        // Re-enable buttons
                        this.$(".btn").prop("disabled", false);
                    }.bind(this)
                )
                .guardedCatch(
                    function () {
                        // Re-enable buttons and remove deleting style (if item was not deleted)
                        this.$(".btn").prop("disabled", false);
                        this.$(".donation-item-" + order_line_id).removeClass("deleting");
                    }.bind(this)
                );
            },
        });

        return publicWidget.registry.GiftPackage;
    });
});