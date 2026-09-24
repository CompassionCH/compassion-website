/** @odoo-module **/

// The auth POSTs can take seconds with no feedback, and a second tap fails CSRF
// and shows a 400 over the reset that already succeeded (T3481).
const AUTH_PATHS = ["/web/login", "/web/signup", "/web/reset_password"];
const RELEASE_MS = 10000;

function showNativeLoader() {
  if (window.nativeLoader) {
    window.nativeLoader.postMessage("show");
  } else if (window.webkit?.messageHandlers?.nativeLoader) {
    window.webkit.messageHandlers.nativeLoader.postMessage("show");
  }
}

if (AUTH_PATHS.some((path) => window.location.pathname.endsWith(path))) {
  let submitting = false;

  document.addEventListener(
    "submit",
    (ev) => {
      if (submitting) {
        ev.preventDefault();
        return;
      }
      submitting = true;
      showNativeLoader();
      // Never hold the form hostage if the navigation never lands.
      window.setTimeout(() => {
        submitting = false;
      }, RELEASE_MS);
    },
    true
  );

  // Restored from the back/forward cache: the form is live again.
  window.addEventListener("pageshow", () => {
    submitting = false;
  });
}
