/** @odoo-module **/

/**
 * Redirect buttons on the custom error page: "Home" -> dashboard, "Contact us"
 * -> the contact page. Bound by the data-custom attribute the theme
 * ThemedButtonComponent emits.
 *
 * Used in /templates/http_error_custom.xml
 */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.RedirectDashboard = publicWidget.Widget.extend({
  selector: "[data-custom='dashboard']",
  events: {
    click: "_onClickDashboard",
  },

  _onClickDashboard() {
    window.location.href = "/my2/dashboard";
  },
});

publicWidget.registry.RedirectContactUs = publicWidget.Widget.extend({
  selector: "[data-custom='contact_us']",
  events: {
    click: "_onClickContactUs",
  },

  _onClickContactUs() {
    window.location.href = "/contactus";
  },
});
