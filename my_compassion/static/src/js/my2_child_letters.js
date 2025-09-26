/**
 * Handles the pagination and adds filtering arguments in the url for the my2_child_letters.xml page.
 * Used in /templates/pages/my2_child_letters.xml.
 */
odoo.define("my_compassion.my2_child_letters", function (require) {
    "use strict";

    const okBtn = document.getElementById("filterOkBtn");
    const ToastService = require("my_compassion.toast_service");
    const _t = require("web.core")._t;
    const rpc = require("web.rpc");

    // Letter animation
    document.querySelectorAll(".my2-envelope").forEach((envelope) => {
        envelope.addEventListener("click", function () {
            envelope.classList.add("open");
            const letter = envelope.querySelector(".env-letter");

            // dataset is retrieved from xml t-att-data attribute
            const letterId = envelope.dataset.letterId;
            const letterRead = envelope.dataset.letterRead;
            const childId = envelope.dataset.childId;

            // Mark letter as read
            if (childId && letterId && !letterRead) {
                rpc.query({
                    route: `/my2/children/${childId}/letters/${letterId}/mark_read`,
                    params: { letter_id: parseInt(letterId) },
                })
                    .then((result) => {
                        console.log("Letter read status updated:", result);
                    })
                    .catch((err) => {
                        console.error("Failed to mark letter as read", err);
                    });
            }

            setTimeout(() => {
                if (letter) {
                    letter.style.zIndex = "3";
                }
            }, 800);

            setTimeout(function () {
                const href = envelope.getAttribute("href");
                if (href) {
                    window.location.href = href;
                }
            }, 1200);
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

            const sort = document.querySelector('input[name="sortOptions"]:checked')?.value || "newest";
            const unreadFilter = document.querySelector('input[name="unreadOptions"]:checked')?.value || "all";

            const redirect_child_id = document.getElementById("childrenDropdown")?.value || "";
            const selectedType = document.querySelector('input[name="type"]:checked')?.value || "";

            const url = new URL(window.location.origin + "/my2/children/letters");
            if (redirect_child_id) url.pathname += `/${redirect_child_id}`;
            if (filterYearFrom) url.searchParams.set("year_from", filterYearFrom);
            if (filterYearTo) url.searchParams.set("year_to", filterYearTo);
            if (filterMonthFrom) url.searchParams.set("month_from", filterMonthFrom);
            if (filterMonthTo) url.searchParams.set("month_to", filterMonthTo);
            if (selectedType) url.searchParams.set("type", selectedType);

            url.searchParams.set("sort", sort);
            url.searchParams.set("unread", unreadFilter); // new filter
            url.searchParams.set("page", 1);

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
                ToastService.error(_t("Sorry, this letter cannot be shared."));
                return;
            }

            // This works only in secure contexts (HTTPS)
            if (navigator.share) {
                try {
                    navigator.share(shareData);
                    console.log("Letter shared successfully");
                } catch (err) {
                    console.error("Share failed:", err.message);
                    ToastService.error(_t("Failed to share letter."));
                }
            } else if (navigator.clipboard) {
                // Fallback for browsers that do not support the Web Share API
                navigator.clipboard
                    .writeText(shareData.url)
                    .then(() => {
                        ToastService.success(_t("Link copied to clipboard!"));
                    })
                    .catch((err) => {
                        console.error("Could not copy text: ", err);
                        ToastService.error(_t("Failed to copy link."));
                    });
            } else {
                // Fallback for browsers that do not support the Web Share API or Clipboard API
                ToastService.error(_t("Sharing is not supported in this browser. Please share your letter manually."));
            }
        });
    });
});
