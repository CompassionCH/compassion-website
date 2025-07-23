/**
 * Infinite Scroll Timeline Loader
 * --------------------------------
 * This script enables infinite scrolling for a timeline component on a child profile page.
 * When the user scrolls near the bottom of the container (#wrapwrap), it loads more timeline
 * entries using AJAX and appends them to the timeline element (.cd-timeline).
 *
 * Key Features:
 * - Fetches timeline data in batches via POST to `/my2/children/<childId>/timeline-batch`
 * - Tracks loading state and prevents duplicate requests
 * - Stops fetching once all records are loaded
 */
document.addEventListener("DOMContentLoaded", () => {
    const timelineEl = document.querySelector(".cd-timeline");
    // In debug mode, you will get an error due to scrollableElement not being defined. The issue lies in the header
    // menu being fixed which create this issue. It does not exist in production.
    const scrollParent = document.querySelector("#wrapwrap");

    // Exit early if required elements are not present
    if (!timelineEl || !scrollParent) return;

    const childId = timelineEl.dataset.childId;
    const loader = timelineEl.querySelector("#timeline-loader");
    const container = timelineEl.querySelector(".content-column");

    let offset = 9;             // Initial offset for loading data
    const limit = 9;            // Number of items to fetch per request
    let isLoading = false;      // Prevents multiple simultaneous requests
    let allLoaded = false;      // Flags when all content has been loaded

    /**
     * Fetches the next batch of timeline entries via AJAX and appends them to the DOM.
     */
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

    /**
     * Scroll handler that triggers loading when user is near the bottom of the container.
     * Can be tweaked to adjust the threshold for loading more data.
     */
    function onScroll() {
        const scrollTop = scrollParent.scrollTop;
        const scrollHeight = scrollParent.scrollHeight;
        const clientHeight = scrollParent.clientHeight;

        if (scrollTop + clientHeight >= scrollHeight - 100) {
            loadMoreData();
        }
    }

    // Attach scroll listener to trigger infinite loading
    scrollParent.addEventListener("scroll", onScroll);
});
