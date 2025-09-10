document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.gift_package", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.GiftPackage = publicWidget.Widget.extend({
            selector: ".my2_gift_package",

            events: {
                "donation-item:edit": "_onDonationItemEdit",
                "donation-item:delete": "_onDonationItemDelete",
                "donation-form:submit": "_onDonationEditSubmit",
            },

            /**
             * @override
             */
            start: function () {
                return this._super.apply(this, arguments);
            },

            /**
             * Handles donation item edit events.
             * @private
             * @param {Event} ev event object.
             */
            _onDonationItemEdit: function (ev) {
                this.order_line_id = ev.detail.order_line_id;

                // Add spinner
                const $spinner = $(
                    '<div class="d-flex justify-content-center align-items-center my-5">' +
                        '<div class="spinner-border text-core-blue" role="status">' +
                        '<span class="sr-only">Loading...</span>' +
                        "</div>" +
                        "</div>"
                );
                $("#edit-donation-form").html($spinner);

                // Show modal
                $("#edit-donation-modal").modal();

                rpc.query({
                    route: "/my2/gift-package/render-edit-form",
                    params: {
                        order_line_id: this.order_line_id,
                    },
                })
                    .then(
                        function (data) {
                            // Replace the form's inner content with the received HTML
                            const $form = $("#edit-donation-form");
                            if (data.html) {
                                $form.html(data.html);

                                // Remove previous widget if there is one
                                if (this.donation_form_widget) {
                                    this.donation_form_widget.destroy();
                                }

                                // Manually instantiate and attach widget
                                this.donation_form_widget = new publicWidget.registry.DonationForm(this);
                                this.donation_form_widget.attachTo($form);
                            }
                        }.bind(this)
                    )
                    .guardedCatch(function () {
                        // Replace spinner with error
                        $("#edit-donation-form").html("Error");
                    });
            },

            /**
             * Handles donation item delete events.
             * @private
             * @param {Event} ev event object.
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
                                this.$("#gift-package-content-wrapper").html(data.html);
                            }
                            // Some elements must be hidden when the order is empty
                            if (data.is_order_empty) {
                                this.$(".empty-order-hidden").hide();
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

            /**
             * Handles donation edit submission event.
             */
            _onDonationEditSubmit: function (ev, data) {
                // Prevent double clicks
                this.$(".btn").prop("disabled", true);

                data.order_line_id = this.order_line_id;

                rpc.query({
                    route: "/my2/gifts/edit",
                    params: data,
                })
                    .then(function (data) {
                        // Redirect user to gift package page
                        window.location.href = "/my2/gift-package";
                    })
                    .guardedCatch(
                        function () {
                            // Re-enable buttons
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    );
            },
        });

        return publicWidget.registry.GiftPackage;
    });
});
