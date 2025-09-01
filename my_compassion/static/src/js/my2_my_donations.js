document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.donations_pager_simple", function (require) {
        "use strict";

        var rpc = require("web.rpc");

        function updateHistory(page) {
            const historyContainer = document.getElementById("donation_history_container");

            if (!historyContainer) {
                console.error("Donation history container not found.");
                return;
            }

            rpc.query({
                route: "/my2/my-donations/history",
                params: {
                    invoice_page: page,
                },
            }).then(function (result) {
                if (result.html) {
                    historyContainer.outerHTML = result.html;
                }
            });
        }

        document.addEventListener("click", function (event) {
            const prevBtn = event.target.closest("#history_pager_prev");
            const nextBtn = event.target.closest("#history_pager_next");

            if (prevBtn) {
                event.preventDefault();
                const page = prevBtn.dataset.page;
                if (page) {
                    updateHistory(page);
                }
            } else if (nextBtn) {
                event.preventDefault();
                const page = nextBtn.dataset.page;
                if (page) {
                    updateHistory(page);
                }
            }
        });
    });
});
