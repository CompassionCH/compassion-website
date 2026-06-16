/** @odoo-module **/

/**
 * Add-a-gift page widget.
 *
 * Toggles the gift/fund product tabs (`.my2-add-a-gift`) and persists the
 * hosted donation form's submission: on `donation-form:submit` it posts the
 * payload to `/my2/gifts/new` and redirects to the gift package.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

export const AddAGift = publicWidget.Widget.extend({
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

        rpc("/my2/gifts/new", data)
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

publicWidget.registry.AddAGift = AddAGift;
