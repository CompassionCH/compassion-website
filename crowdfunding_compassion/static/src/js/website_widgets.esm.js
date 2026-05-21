import publicWidget from "@web/legacy/js/public/public_widget";

// DONATION FORM
publicWidget.registry.CrowdfundingDonationForm = publicWidget.Widget.extend({
  selector: "#project_donation_page",

  start: function () {
    const result = this._super(...arguments);

    // For page 1 and 3, submit the embedded form.
    const submitButton = this.$("#submit");
    const form = this.$("form");
    const page = this.$("#page").val();
    submitButton.on("click", () => {
      if (page !== "2") {
        form.trigger("submit");
      }
    });

    // For page 2, redirect to the action page by updating the CTA href.
    const donationTypeButton = this.$('input[name="donation-type"]');
    const actionUrl = this.$("#action_url").data("action_url");
    donationTypeButton.on("change", function () {
      if (this.checked) {
        submitButton.attr("href", JSON.parse(actionUrl.replace(/'/g, '"'))[this.value]);
        if (this.value === "product") {
          submitButton.attr("target", "");
        } else {
          submitButton.attr("target", "_blank");
        }
      }
    });
    donationTypeButton.trigger("change");

    return result;
  },
});

// Handle donation card selection
publicWidget.registry.CustomAmountSelection = publicWidget.Widget.extend({
  selector: "#custom-amount-card",
  events: {
    click: "_checkCustomCard",
  },

  start: function () {
    const result = this._super(...arguments);

    // Attach click event listener to all card options except custom amount card.
    const otherCardsInputs = this.$('input[name="amount"]:not(#custom-amount-card)');
    otherCardsInputs.each((_, card) => {
      $(card).on("click", this._onCardClick.bind(this));
    });

    // Attach input event listener to custom amount field when available.
    const customAmountField = this.$("#custom-amount-field");
    if (customAmountField.length) {
      customAmountField.on("input", this._onInput.bind(this));
    }

    return result;
  },

  // Check the custom amount card when custom amount field changes.
  _onInput: function () {
    const customAmountField = this.$("#custom-amount-field");

    if (customAmountField.length) {
      const amount = String(customAmountField.val() || "").trim();
      const isAmountNotEmpty = amount !== "";

      if (isAmountNotEmpty) {
        this._checkCustomCard();
      }
    }
  },

  // Check the custom amount card and uncheck the others.
  _checkCustomCard: function () {
    const customAmountCard = this.$("#custom-amount-card");
    const otherCardsInputs = this.$(
      'input[name="amount"]:not(#custom-amount-card):not(#custom-amount-field)'
    );

    if (customAmountCard.length) {
      customAmountCard.prop("checked", true);

      otherCardsInputs.each((_, input) => {
        $(input).prop("checked", false);
      });
    }
  },

  // Uncheck the custom amount card when any other card option is clicked.
  _onCardClick: function () {
    const customAmountCard = this.$("#custom-amount-card");
    if (customAmountCard.length) {
      customAmountCard.prop("checked", false);
    }
  },
});

// EDIT PROJECT FORM
publicWidget.registry.EditProjectForm = publicWidget.Widget.extend({
  selector: "#project_update_form",

  start: function () {
    const result = this._super(...arguments);
    this._setupDefaultValues();
    return result;
  },

  _setupDefaultValues: function () {
    // Set date field default value.
    const formValues = this.$("#form_values");
    const deadline = formValues.data("deadline");
    if (deadline) {
      this.$('input[name="deadline"]').val(new Date(deadline).toLocaleDateString());
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
    const result = this._super(...arguments);

    this.$("[id^=product-choose-]").on("click", function () {
      // Show the product settings.
      const buttonId = this.getAttribute("id");
      const idArray = buttonId.split("-");
      const productIndex = idArray[idArray.length - 1];
      $("[id^=fund-settings-]").hide();
      $("#fund-settings-" + productIndex).show();
      // Copy product_id to real form.
      const productId = $("#product-id-" + productIndex).val();
      $("#product_id").val(productId);
    });

    // If the number of participant is set, it should appear in the corresponding widget.
    if ($("#participant_product_number_goal").val()) {
      $("[id^=fund-number-]").val($("#participant_product_number_goal").val());
    }

    this.$("[id^=fund-number-]").on("change", function () {
      // Copy fund amount to real form.
      $("#product_number_goal").val($(this).val());
    });

    // If the number of sponsorship is set, it should appear in the corresponding widget.
    if ($("#participant_number_sponsorships_goal").val()) {
      $("#number-sponsorships").val($("#participant_number_sponsorships_goal").val());
    }

    this.$("#number-sponsorships").on("change", function () {
      // Copy sponsorship goal to real form.
      $("#participant_number_sponsorships_goal").val($(this).val());
    });

    // Hide required fields legend.
    $(".above-controls").hide();

    // Show the correct social media help text depending on the project type.
    this.$("select#type").on("change", function () {
      const value = $(this).val();
      const help = $("#social_medias .fieldset-description");
      const webLabel = $("label[for=personal_web_page_url]");
      const webInput = $("input#personal_web_page_url");
      let webText = "";
      if (value === "individual") {
        help.html($("#individual_media_help").text());
        webText = $("#individual_url_help").text();
        webLabel.html(webText);
        webInput.attr("placeholder", webText);
      } else {
        help.html($("#collective_media_help").text());
        webText = $("#collective_url_help").text();
        webLabel.html(webText);
        webInput.attr("placeholder", webText);
      }
    });

    return result;
  },
});
