odoo.define("website_event_compassion.donation_form", function (require) {
  "use strict";

  let publicWidget = require("web.public.widget");

  publicWidget.registry.DonationForm = publicWidget.Widget.extend({
    selector: "#event_donation_form",

    start: function () {
      $(".amount_button").on("click", function () {
        $("#input_amount").val($(this).data("donation-value"));
      });
      $("#amount_custom_input").on("change", function () {
        $("#input_amount").val($(this).val());
      });
      this.$("form").submit(function (e) {
        if (!$("#input_amount").val()) {
          e.preventDefault();
          $(".error").hide().removeClass("d-none").fadeIn();
        }
      });
    },
  });
});
