import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.EventRegistrationForm = publicWidget.Widget.extend({
  selector: "#event_registration_form",

  start() {
    this._setupDefaultValues();
    const phoneInput = this.el.querySelector("input[name='partner_phone']");
    const mobileInput = this.el.querySelector("input[name='partner_mobile']");
    if (phoneInput) {
      phoneInput.addEventListener("change", () => {
        const hiddenPhone = this.el.querySelector("input[name='phone']");
        if (hiddenPhone) {
          hiddenPhone.value = phoneInput.value;
        }
      });
    }
    if (mobileInput) {
      mobileInput.addEventListener("change", () => {
        const hiddenMobile = this.el.querySelector("input[name='mobile']");
        if (hiddenMobile) {
          hiddenMobile.value = mobileInput.value;
        }
      });
    }
    return this._super(...arguments);
  },

  _setupDefaultValues() {
    const formValuesEl = this.el.querySelector("#form_values");
    if (!formValuesEl) {
      return;
    }
    const formValues = formValuesEl.dataset;
    const eventId = formValues.event_id;
    if (eventId) {
      const eventSelect = this.el.querySelector("select[name='event_id']");
      if (eventSelect) {
        eventSelect.value = eventId;
      }
    }
    const selectFields = ["partner_title"];
    for (const sField of selectFields) {
      if (formValues[sField]) {
        const selectEl = this.el.querySelector(`select[name='${sField}']`);
        if (selectEl) {
          selectEl.value = formValues[sField];
        }
      }
    }
    const birthdate = formValues.partner_birthdate_date;
    if (birthdate) {
      const birthdateInput = this.el.querySelector(
        "input[name='partner_birthdate_date']"
      );
      if (birthdateInput) {
        birthdateInput.value = new Date(birthdate).toLocaleDateString();
      }
    }
  },
});

export default publicWidget.registry.EventRegistrationForm;
