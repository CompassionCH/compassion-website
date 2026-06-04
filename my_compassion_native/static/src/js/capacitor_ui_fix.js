odoo.define("my_compassion_native.capacitor_ui_fix", function () {
    "use strict";

    $(function () {
        if (!window.Capacitor || window.Capacitor.getPlatform() === "web") return;

        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState !== "visible") return;

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
});
