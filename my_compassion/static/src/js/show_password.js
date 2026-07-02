/** @odoo-module **/

import {whenReady} from "@odoo/owl";

/**
 * Show/hide toggle for the standard login and signup password inputs.
 *
 * The my2 pages render the theme Password component, which ships its own
 * toggle; this module animates the `#eye_password` / `#eye_confirm_password`
 * icons that the plain (non-my2) login and signup templates inject next to
 * the core inputs. It binds only when those ids exist on the page.
 */
function togglePasswordVisibility(inputId, icon) {
  const input = document.getElementById(inputId);
  if (input) {
    if (input.type === "password") {
      input.type = "text";
      icon.classList.add("fa-eye-slash");
      icon.classList.remove("fa-eye");
    } else {
      input.type = "password";
      icon.classList.add("fa-eye");
      icon.classList.remove("fa-eye-slash");
    }
  }
}

function addPasswordToggleListener(eyeId, inputId) {
  const eyeIcon = document.getElementById(eyeId);
  if (eyeIcon) {
    eyeIcon.addEventListener("click", function () {
      togglePasswordVisibility(inputId, eyeIcon);
    });
  }
}

whenReady(() => {
  addPasswordToggleListener("eye_password", "password");
  addPasswordToggleListener("eye_confirm_password", "confirm_password");
});
