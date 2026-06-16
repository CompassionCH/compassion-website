/** @odoo-module **/

/**
 * Donation history pager.
 *
 * Listens document-wide for clicks on the history pager buttons
 * (`#history_pager_prev` / `#history_pager_next`), fetches the requested
 * page from `/my2/donations/history` and swaps `#donation_history_container`
 * with the returned markup. A re-entrancy guard ignores clicks while a page
 * load is in flight.
 */

import { rpc } from "@web/core/network/rpc";

let isUpdating = false;

function updateHistory(page) {
    if (isUpdating) {
        return;
    }

    const historyContainer = document.getElementById("donation_history_container");
    const pagerButtons = document.querySelectorAll("#history_pager_prev, #history_pager_next");

    if (!historyContainer) {
        console.error("Donation history container not found.");
        return;
    }

    isUpdating = true;
    pagerButtons.forEach((btn) => btn.classList.add("disabled"));

    rpc("/my2/donations/history", {
        invoice_page: page,
    })
        .then(function (result) {
            if (result.html) {
                historyContainer.outerHTML = result.html;
            }
        })
        .finally(() => {
            isUpdating = false;
            document.querySelectorAll("#history_pager_prev, #history_pager_next").forEach((btn) => {
                if (btn) btn.classList.remove("disabled");
            });
        });
}

document.addEventListener("click", function (event) {
    const btn = event.target.closest("#history_pager_prev, #history_pager_next");
    if (btn) {
        event.preventDefault();
        const page = btn.dataset.page;
        if (page) {
            updateHistory(page);
        }
    }
});
