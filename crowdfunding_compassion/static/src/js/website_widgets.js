odoo.define("crowdfunding_compassion.website_widgets", function (require) {
  "use strict";

  const publicWidget = require("web.public.widget");

  // DONATION FORM
  publicWidget.registry.DonationForm = publicWidget.Widget.extend({
    selector: "#project_donation_page",

    start: function () {
      // For page 1 and 3, we submit the embedded form
      const submit_button = this.$("#submit");
      const form = this.$("form");
      const page = this.$("#page").val();
      submit_button.click(() => {
        if (page !== "2") form.submit();
      });

      // For page 2, we redirect to the action page (by setting the href attribute)
      const donation_type_button = this.$('input[name="donation-type"]');
      const action_url = this.$("#action_url").data("action_url");
      donation_type_button.change(function () {
        if (this.checked) {
          submit_button.attr(
            "href",
            JSON.parse(action_url.replace(/'/g, '"'))[this.value]
          );
          if (this.value !== "product") submit_button.attr("target", "_blank");
          else submit_button.attr("target", "");
        }
      });
    },
  });

  // EDIT PROJECT FORM
  publicWidget.registry.EditProjectForm = publicWidget.Widget.extend({
    selector: "#project_update_form",

    start: function () {
      this.setup_default_values();
    },

    setup_default_values: function () {
      // This is to set correctly the date field default value
      const form_values = $("#form_values");
      const form = $("#project_update_form");
      const deadline = form_values.data("deadline");
      if (deadline) {
        console.log(deadline);
        form
          .find('input[name="deadline"]')
          .val(new Date(deadline).toLocaleDateString());
      }
    },
  });

  // PROJECT CREATION FORM
  publicWidget.registry.CreateProjectForm = publicWidget.Widget.extend({
    selector: ".crowdfunding_project_creation_from",

    /**
     * Called when widget is started.
     */
    start: function () {
      $("[id^=product-choose-]").click(function () {
        // Show the product settings
        var button_id = this.getAttribute("id");
        var id_array = button_id.split("-");
        var product_index = id_array[id_array.length - 1];
        $("[id^=fund-settings-]").hide();
        $("#fund-settings-" + product_index).show();
        // Copy product_id to real form
        var product_id = $("#product-id-" + product_index).val();
        $("#product_id").val(product_id);
      });

      // If the number of participant is set, it should appear in the corresponding widget
      if ($("#participant_product_number_goal").val()) {
        $("[id^=fund-number-]").val(
          $("#participant_product_number_goal").val()
        );
      }

      $("[id^=fund-number-]").change(function () {
        // Copy fund amount to real form
        $("#product_number_goal").val($(this).val());
      });

      // If the number of sponsorship is set, it should appear in the corresponding widget
      if ($("#participant_number_sponsorships_goal").val()) {
        $("#number-sponsorships").val(
          $("#participant_number_sponsorships_goal").val()
        );
      }

      $("#number-sponsorships").change(function () {
        // Copy sponsorship goal to real form
        $("#participant_number_sponsorships_goal").val($(this).val());
      });

      // Hide required fields legend
      $(".above-controls").hide();

      // Show the correct social media help text depending on the project type
      $("select#type").change(function () {
        var value = $(this).val();
        var help = $("#social_medias .fieldset-description");
        var web_label = $("label[for=personal_web_page_url]");
        var web_input = $("input#personal_web_page_url");
        var web_text = "";
        if (value === "individual") {
          help.html($("#individual_media_help").text());
          web_text = $("#individual_url_help").text();
          web_label.html(web_text);
          web_input.attr("placeholder", web_text);
        } else {
          help.html($("#collective_media_help").text());
          web_text = $("#collective_url_help").text();
          web_label.html(web_text);
          web_input.attr("placeholder", web_text);
        }
      });
    },
  });
});
