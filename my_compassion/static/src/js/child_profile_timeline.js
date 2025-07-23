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

    let offset = 9; // Initial offset for loading data
    const limit = 9; // Number of items to fetch per request
    let isLoading = false; // Prevents multiple simultaneous requests
    let allLoaded = false; // Flags when all content has been loaded

    // --- Timeline animation logic (based on CodyHouse) ---
    class VerticalTimeline {
        constructor(element) {
            this.element = element;
            this.offset = 0.8;
            this.updateBlocks(); // initialize references
            this.hideBlocks(); // initial hide
        }

        updateBlocks() {
            this.blocks = this.element.querySelectorAll(".cd-timeline__block");
            this.images = this.element.querySelectorAll(".cd-timeline__img");
            this.contents = this.element.querySelectorAll(".cd-timeline__content");
        }

        hideBlocks() {
            if (!("classList" in document.documentElement)) return;
            this.blocks.forEach((block, i) => {
                if (i < 3) return;
                if (block.getBoundingClientRect().top > window.innerHeight * this.offset) {
                    this.images[i].classList.add("cd-timeline__img--hidden");
                    this.contents[i].classList.add("cd-timeline__content--hidden");
                }
            });
        }

        showBlocks() {
            if (!("classList" in document.documentElement)) return;
            this.blocks.forEach((block, i) => {
                if (
                    this.contents[i].classList.contains("cd-timeline__content--hidden") &&
                    block.getBoundingClientRect().top <= window.innerHeight * this.offset
                ) {
                    this.images[i].classList.add("cd-timeline__img--bounce-in");
                    this.contents[i].classList.add("cd-timeline__content--bounce-in");
                    this.images[i].classList.remove("cd-timeline__img--hidden");
                    this.contents[i].classList.remove("cd-timeline__content--hidden");
                }
            });
        }
    }

    const timelineInstance = new VerticalTimeline(timelineEl);

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

        // Animate visible timeline blocks
        timelineInstance.showBlocks();
    }

    // Attach scroll listener to trigger infinite loading
    scrollParent.addEventListener("scroll", onScroll);

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

                    // After inserting new HTML, re-scan and animate
                    timelineInstance.updateBlocks();
                    timelineInstance.hideBlocks(); // Mark hidden
                    timelineInstance.showBlocks(); // Animate if in view
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

    // Initial check (in case first blocks are already visible)
    timelineInstance.showBlocks();
});
