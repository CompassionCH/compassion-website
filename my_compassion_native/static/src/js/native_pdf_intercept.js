/** @odoo-module **/

import {downloadAndOpenPDF} from "@my_compassion_native/js/capacitor_pdf_util";
import {whenReady} from "@odoo/owl";

whenReady(() => {
  if (!window.Capacitor || window.Capacitor.getPlatform() === "web") {
    return;
  }

  document.addEventListener("click", function (event) {
    const link = event.target.closest(
      'a[href*="/download/"], a[href*="/report/pdf/"], a[href$=".pdf"], a[href*="/b2s_image"]'
    );
    if (!link) {
      return;
    }

    const href = link.getAttribute("href");
    if (!href || href === "#" || href.startsWith("javascript")) {
      return;
    }

    event.preventDefault();
    const url = href.startsWith("http") ? href : window.location.origin + href;
    const raw = href.split("/").pop().split("?")[0];
    const filename = raw.endsWith(".pdf") ? raw : raw + ".pdf";
    downloadAndOpenPDF(url, filename);
  });
});
