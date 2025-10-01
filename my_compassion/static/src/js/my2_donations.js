document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.donations_pager_simple", function (require) {
        "use strict";

        var rpc = require("web.rpc");
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
            pagerButtons.forEach(btn => btn.classList.add('disabled'));

            rpc.query({
                route: "/my2/donations/history",
                params: {
                    invoice_page: page,
                },
            }).then(function (result) {
                if (result.html) {
                    historyContainer.outerHTML = result.html;
                }
            }).finally(() => {
                    isUpdating = false;
                    document.querySelectorAll("#history_pager_prev, #history_pager_next").forEach(btn => {
                    if(btn) btn.classList.remove('disabled');
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
    });
});
