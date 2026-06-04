odoo.define("my_compassion_native.native_pdf_intercept", function (require) {
    "use strict";

    const CapacitorPdfUtil = require("my_compassion_native.capacitor_pdf_util");

    $(function () {
        if (!window.Capacitor || window.Capacitor.getPlatform() === "web") return;

        document.addEventListener("click", function (event) {
            const link = event.target.closest(
                'a[href*="/download/"], a[href*="/report/pdf/"], a[href$=".pdf"], a[href*="/b2s_image"]'
            );
            if (!link) return;

            const href = link.getAttribute("href");
            if (!href || href === "#" || href.startsWith("javascript")) return;

            event.preventDefault();
            const url = href.startsWith("http") ? href : window.location.origin + href;
            const raw = href.split("/").pop().split("?")[0];
            const filename = raw.endsWith(".pdf") ? raw : raw + ".pdf";
            CapacitorPdfUtil.downloadAndOpenPDF(url, filename);
        });
    });
});
