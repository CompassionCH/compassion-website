/* Adds a bridge for Odoo to detect when it's running inside the Capacitor native app shell.
   This allows us to apply native-specific styles and behaviors.
 */
(function () {
  function initCapacitorFixes() {
    if (!window.Capacitor || window.Capacitor.getPlatform() === "web") return;

    console.log("Capacitor Bridge: Native environment detected. Applying fixes...");
    document.body.classList.add("is-native-app");

    document.querySelectorAll('meta[name="viewport"]').forEach(function (vp) {
      if (vp.content.indexOf("viewport-fit=cover") === -1) {
        vp.content += ", viewport-fit=cover";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCapacitorFixes);
  } else {
    initCapacitorFixes();
  }
})();
