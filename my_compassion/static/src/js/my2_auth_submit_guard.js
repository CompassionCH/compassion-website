/** @odoo-module **/

// The auth POSTs can take seconds with no feedback, and a second tap fails CSRF
// and shows a 400 over the reset that already succeeded (T3481).
const AUTH_PATHS = ["/web/login", "/web/signup", "/web/reset_password"];
const RELEASE_MS = 15000;

function showNativeLoader() {
  if (window.nativeLoader) {
    window.nativeLoader.postMessage("show");
  } else if (window.webkit?.messageHandlers?.nativeLoader) {
    window.webkit.messageHandlers.nativeLoader.postMessage("show");
  }
}

if (AUTH_PATHS.some((path) => window.location.pathname.endsWith(path))) {
  let submitting = false;
  const release = () => {
    submitting = false;
  };

  document.addEventListener(
    "submit",
    (ev) => {
      if (submitting) {
        ev.preventDefault();
        return;
      }
      submitting = true;
      showNativeLoader();
      // A navigation that never commits fires no event, so the form can only
      // free itself once no response can plausibly still arrive.
      window.setTimeout(release, RELEASE_MS);
    },
    true
  );

  // Restored from the back/forward cache: the form is live again.
  window.addEventListener("pageshow", release);
}
