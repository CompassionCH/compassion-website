/** @odoo-module **/

// The auth POSTs can take seconds with no feedback, and a second tap fails CSRF
// and shows a 400 over the reset that already succeeded (T3481).
const AUTH_PATHS = ["/web/login", "/web/signup", "/web/reset_password"];

function showNativeLoader() {
  if (window.nativeLoader) {
    window.nativeLoader.postMessage("show");
  } else if (window.webkit?.messageHandlers?.nativeLoader) {
    window.webkit.messageHandlers.nativeLoader.postMessage("show");
  }
}

if (AUTH_PATHS.some((path) => window.location.pathname.endsWith(path))) {
  document.addEventListener(
    "submit",
    (ev) => {
      const form = ev.target;
      if (form.dataset.my2Submitting) {
        ev.preventDefault();
        return;
      }
      form.dataset.my2Submitting = "1";
      showNativeLoader();
      const button = form.querySelector("button[type='submit'], button:not([type])");
      if (button) {
        // Disabling it before the browser serializes would drop its value.
        setTimeout(() => {
          button.disabled = true;
        }, 0);
      }
    },
    true
  );
}
