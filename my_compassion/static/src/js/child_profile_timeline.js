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

    function loadMoreData() {
        if (isLoading || allLoaded) return;

        isLoading = true;
        loader.style.display = "block";


        fetch(`/my2/children/${childId}/timeline-batch`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest", // Tells Odoo it's an AJAX call
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    offset,
                    limit,
                },
            }),
        })
            .then((res) => res.json())
            .then((data) => {
                const html = data.result?.html || "";
                const hasMore = data.result?.has_more_records;

                if (html.trim()) {
                    container.insertAdjacentHTML("beforeend", html);
                    offset += limit;
                    allLoaded = !hasMore;
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
