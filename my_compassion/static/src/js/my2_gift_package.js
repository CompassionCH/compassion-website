/** @odoo-module **/

/**
 * Gift package (cart) page widget.
 *
 * Manages the donation lines of the gift package (`.my2_gift_package`):
 * opens the edit modal and re-renders a donation form inside it
 * (`/my2/gift-package/render-edit-form`), persists edits
 * (`/my2/gifts/edit`), and deletes lines (`/my2/gift-package/delete-item`).
 * The edit/delete buttons in the line templates dispatch the
 * `donation-item:edit` / `donation-item:delete` custom events this widget
 * listens to, carrying the order line id in `detail`.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { DonationForm } from "@my_compassion/js/my2_donation_form";

export const GiftPackage = publicWidget.Widget.extend({
    selector: ".my2_gift_package",

    events: {
        "donation-item:edit": "_onDonationItemEdit",
        "donation-item:delete": "_onDonationItemDelete",
        "donation-form:submit": "_onDonationEditSubmit",
    },

    /**
     * Handles donation item edit events.
     * @private
     * @param {Event} ev event object.
     */
    _onDonationItemEdit: function (ev) {
        this.order_line_id = (ev.detail || ev.originalEvent.detail).order_line_id;

        // Add spinner
        const $spinner = $(
            '<div class="d-flex justify-content-center align-items-center my-5">' +
                '<div class="spinner-border text-core-blue" role="status">' +
                '<span class="visually-hidden">Loading...</span>' +
                "</div>" +
                "</div>"
        );
        $("#edit-donation-form").html($spinner);

        // Show modal
        Modal.getOrCreateInstance(document.getElementById("edit-donation-modal")).show();

        rpc("/my2/gift-package/render-edit-form", {
            order_line_id: this.order_line_id,
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
                        this.donation_form_widget = new DonationForm(this);
                        this.donation_form_widget.attachTo($form);
                    }
                }.bind(this)
            )
            .catch(function () {
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
        const order_line_id = (ev.detail || ev.originalEvent.detail).order_line_id;

        // Disable buttons and apply deleting style
        this.$(".btn").prop("disabled", true);
        this.$(".donation-item-" + order_line_id).addClass("deleting");

        rpc("/my2/gift-package/delete-item", {
            order_line_id: order_line_id,
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
            .catch(
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

        rpc("/my2/gifts/edit", data)
            .then(function () {
                // Redirect user to gift package page
                window.location.href = "/my2/gift-package";
            })
            .catch(
                function () {
                    // Re-enable buttons
                    this.$(".btn").prop("disabled", false);
                }.bind(this)
            );
    },
});

publicWidget.registry.GiftPackage = GiftPackage;
