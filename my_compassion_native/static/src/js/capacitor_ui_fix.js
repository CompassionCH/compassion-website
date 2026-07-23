/** @odoo-module **/

import {whenReady} from "@odoo/owl";

// On returning to the app, clear any leftover blocking overlay / spinner that
// the WebView may have frozen while backgrounded.
whenReady(() => {
  if (!window.Capacitor || window.Capacitor.getPlatform() === "web") {
    return;
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") {
      return;
    }

    if (window.$ && window.$.unblockUI) {
      window.$.unblockUI();
    }
    document.querySelectorAll("div").forEach((el) => {
      if (el.style.zIndex === "9999999" || el.innerHTML.includes("click-spin")) {
        el.style.display = "none";
      }
    });
  });
});
