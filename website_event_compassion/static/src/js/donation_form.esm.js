import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.EventDonationForm = publicWidget.Widget.extend({
  selector: "#event_donation_form",

  events: {
    "click .amount_button": "_onAmountButtonClick",
    "change #amount_custom_input": "_onAmountCustomInputChange",
    "submit form": "_onFormSubmit",
  },

  _onAmountButtonClick(ev) {
    const inputAmount = this.el.querySelector("#input_amount");
    if (inputAmount) {
      $(".amount_button").removeClass("active");
      $(ev.currentTarget).addClass("active");
      inputAmount.value = ev.currentTarget.dataset.donationValue;
    }
  },

  _onAmountCustomInputChange(ev) {
    const inputAmount = this.el.querySelector("#input_amount");
    if (inputAmount) {
      inputAmount.value = ev.currentTarget.value;
    }
  },

  _onFormSubmit(ev) {
    const inputAmount = this.el.querySelector("#input_amount");
    if (!inputAmount || !inputAmount.value) {
      ev.preventDefault();
      const errorEl = this.el.querySelector(".error");
      if (errorEl) {
        errorEl.classList.remove("d-none");
        errorEl.style.display = "";
      }
    }
  },
});

export default publicWidget.registry.EventDonationForm;
