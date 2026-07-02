/** @odoo-module **/

/**
 * Handles the pagination and adds filtering arguments in the url for the my2_child_letters.xml page.
 * Used in /templates/pages/my2_child_letters.xml.
 */

import {_t} from "@web/core/l10n/translation";
import {toast} from "@my_compassion/js/toast_service";
import {whenReady} from "@odoo/owl";

whenReady(() => {
  const okBtn = document.getElementById("filterOkBtn");

  // Letter animation
  document.querySelectorAll(".my2-envelope").forEach((envelope) => {
    envelope.addEventListener("click", function () {
      const letter = envelope.querySelector(".env-letter");
      const target = envelope.dataset.target || "_self";

      if (!envelope.classList.contains("already-read")) {
        // Iframe
        const iframeContainer = envelope.querySelector(".iframe-container");
        let iframe = iframeContainer.querySelector("iframe");
        if (!iframe) {
          iframe = document.createElement("iframe");
          iframe.src =
            "/b2s_image?id=" +
            envelope.dataset.letterUuid +
            "&disposition=inline&file_type=pdf";
          iframe.type = "application/pdf";
          iframeContainer.appendChild(iframe);
          iframeContainer.style.display = "block";

          iframe.addEventListener("load", () => {
            envelope.classList.add("open");
          });
        } else {
          envelope.classList.add("open");
        }

        // The z-index has to change dynamically during the animation
        setTimeout(() => {
          if (letter) {
            letter.style.zIndex = "3";
          }
        }, 800);

        setTimeout(function () {
          const href = envelope.getAttribute("href");
          if (href) {
            window.open(
              href,
              target,
              target === "_blank" ? "noopener,noreferrer" : null
            );
          }
        }, 1400);
      } else {
        envelope.classList.remove("open");
        envelope.classList.add("reopen");

        setTimeout(function () {
          const href = envelope.getAttribute("href");
          if (href) {
            window.open(
              href,
              target,
              target === "_blank" ? "noopener,noreferrer" : null
            );
          }
        }, 600);
      }
    });
  });

  // Pagination: Next Page
  document.getElementById("nextPageBtn")?.addEventListener("click", () => {
    const currentUrl = new URL(window.location.href);
    const currentPage = parseInt(currentUrl.searchParams.get("page") || "1", 10);
    currentUrl.searchParams.set("page", currentPage + 1);
    window.location.href = currentUrl.toString();
  });

  // Pagination: Previous Page
  document.getElementById("prevPageBtn")?.addEventListener("click", () => {
    const currentUrl = new URL(window.location.href);
    const currentPage = parseInt(currentUrl.searchParams.get("page") || "1", 10);
    if (currentPage > 1) {
      currentUrl.searchParams.set("page", currentPage - 1);
      window.location.href = currentUrl.toString();
    }
  });

  // Apply filters and sorting when OK button is clicked
  if (okBtn) {
    okBtn.addEventListener("click", function () {
      const filterYearFrom = document.getElementById("yearDropdownFrom")?.value || "";
      const filterYearTo = document.getElementById("yearDropdownTo")?.value || "";
      const filterMonthFrom = document.getElementById("monthDropdownFrom")?.value || "";
      const filterMonthTo = document.getElementById("monthDropdownTo")?.value || "";
      const filterUnread = document.querySelector(
        'input[name="unreadOptions"]:checked'
      );

      const sort =
        document.querySelector('input[name="sortOptions"]:checked')?.value || "newest";
      const redirect_child_id =
        document.getElementById("childrenDropdown")?.value || "";
      const selectedType =
        document.querySelector('input[name="type"]:checked')?.value || "";

      const url = new URL(window.location.origin + "/my2/children/letters");
      if (redirect_child_id) url.searchParams.set("child_id", redirect_child_id);
      if (filterYearFrom) url.searchParams.set("year_from", filterYearFrom);
      if (filterYearTo) url.searchParams.set("year_to", filterYearTo);
      if (filterMonthFrom) url.searchParams.set("month_from", filterMonthFrom);
      if (filterMonthTo) url.searchParams.set("month_to", filterMonthTo);
      if (selectedType) url.searchParams.set("type", selectedType);

      url.searchParams.set("sort", sort);
      url.searchParams.set("page", 1);

      if (filterUnread && filterUnread.value === "unread") {
        url.searchParams.set("unread", "true");
      } else {
        url.searchParams.delete("unread");
      }

      window.location.href = url.toString();
    });
  }

  // Share button functionality
  document.querySelectorAll(".js_share_letter").forEach((shareButton) => {
    shareButton.addEventListener("click", function (ev) {
      ev.preventDefault();
      const shareData = {
        title: this.dataset.shareTitle,
        text: this.dataset.shareText,
        url: this.dataset.shareUrl,
      };

      // Ensure the URL exists before proceeding
      if (!shareData.url) {
        console.error("Share URL is not available for this item.");
        toast.error(_t("Sorry, this letter cannot be shared."));
        return;
      }

      // This works only in secure contexts (HTTPS)
      if (navigator.share) {
        try {
          navigator.share(shareData);
          console.log("Letter shared successfully");
        } catch (err) {
          console.error("Share failed:", err.message);
          toast.error(_t("Failed to share letter."));
        }
      } else if (navigator.clipboard) {
        // Fallback for browsers that do not support the Web Share API
        navigator.clipboard
          .writeText(shareData.url)
          .then(() => {
            toast.success(_t("Link copied to clipboard!"));
          })
          .catch((err) => {
            console.error("Could not copy text: ", err);
            toast.error(_t("Failed to copy link."));
          });
      } else {
        // Fallback for browsers that do not support the Web Share API or Clipboard API
        toast.error(
          _t(
            "Sharing is not supported in this browser. Please share your letter manually."
          )
        );
      }
    });
  });
});
