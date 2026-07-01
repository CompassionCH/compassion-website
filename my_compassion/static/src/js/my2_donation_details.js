/** @odoo-module **/

/**
 * Donation details page widget.
 *
 * Hosts a donation form (`.my2_donation_details`) and persists its
 * submission: on the `donation-form:submit` event it posts the donation
 * payload to `/my2/gifts/new` and redirects to the gift package.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

export const DonationDetails = publicWidget.Widget.extend({
  selector: ".my2_donation_details",

  events: {
    "donation-form:submit": "_onSubmit",
  },

  /**
   * Handles donation submission event.
   */
  _onSubmit: function (ev, data) {
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

publicWidget.registry.DonationDetails = DonationDetails;
