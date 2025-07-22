odoo.define("my_compassion.child_profile_timeline", function (require) {
    "use strict";

    const ajax = require("web.ajax");

    document.addEventListener("DOMContentLoaded", () => {
        const timelineEl = document.querySelector(".cd-timeline");
        const scrollParent = document.querySelector("#wrapwrap");

        if (!timelineEl || !scrollParent) return;

        const childId = timelineEl.dataset.childId;
        const loader = timelineEl.querySelector("#timeline-loader");
        const container = timelineEl.querySelector(".content-column");

        let offset = 9;
        const limit = 9;
        let isLoading = false;
        let allLoaded = false;

        const formData = new FormData();
        formData.append("offset", offset);
        formData.append("limit", limit);

        function loadMoreData() {
            if (isLoading || allLoaded) return;

            isLoading = true;
            loader.style.display = "block";

            ajax.jsonRpc(`/my2/children/${childId}/timeline-batch`, "call", {
                offset,
                limit,
            })
                .then((data) => {
                    if (data.html.trim()) {
                        container.insertAdjacentHTML("beforeend", data.html);
                        offset += limit;
                        allLoaded = !data.has_more_records;
                    } else {
                        allLoaded = true;
                    }
                })
                .catch((err) => {
                    console.error("Error loading timeline data:", err);
                })
                .finally(() => {
                    isLoading = false;
                    loader.style.display = "none";
                });
        }

        function onScroll() {
            const scrollTop = scrollParent.scrollTop;
            const scrollHeight = scrollParent.scrollHeight;
            const clientHeight = scrollParent.clientHeight;

            if (scrollTop + clientHeight >= scrollHeight - 100) {
                loadMoreData();
            }
        }

        scrollParent.addEventListener("scroll", onScroll);
    });
});
