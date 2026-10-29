import {ReCaptcha} from "@google_recaptcha/js/recaptcha";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * The email step of a visitor's donation gates the public payment form:
 * send it with a reCAPTCHA token (when a reCAPTCHA key is configured), as
 * the signup form does.
 */
publicWidget.registry.My2DonorCaptcha = publicWidget.Widget.extend({
  selector: ".my2-gift-package-donor-form",
  events: {
    submit: "_onSubmit",
  },

  init() {
    this._super(...arguments);
    this._recaptcha = new ReCaptcha();
  },

  async willStart() {
    return this._recaptcha.loadLibs();
  },

  _onSubmit(ev) {
    if (
      !this._recaptcha._publicKey ||
      this.el.querySelector("input[name='recaptcha_token_response']")
    ) {
      return;
    }
    ev.preventDefault();
    this._recaptcha.getToken("my2_donor").then((tokenCaptcha) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "recaptcha_token_response";
      input.value = tokenCaptcha.token || "";
      this.el.append(input);
      this.el.submit();
    });
  },
});
