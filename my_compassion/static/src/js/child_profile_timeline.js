/** @odoo-module **/

/**
 * Infinite Scroll Timeline Loader
 * -------------------------------
 * Enables infinite scrolling for the child-profile timeline: when the user
 * scrolls near the bottom of #wrapwrap it fetches the next batch from
 * /my2/children/<childId>/timeline-batch and appends it to .cd-timeline.
 */

import {rpc} from "@web/core/network/rpc";
import {whenReady} from "@odoo/owl";

whenReady(() => {
  const timelineEl = document.querySelector(".cd-timeline");
  // In debug mode, you will get an error due to scrollableElement not being defined. The issue lies in the header
  // menu being fixed which create this issue. It does not exist in production.
  const scrollParent = document.querySelector("#wrapwrap");

  // Exit early if required elements are not present
  if (!timelineEl || !scrollParent) return;

  const childId = timelineEl.dataset.childId;
  const loader = timelineEl.querySelector("#timeline-loader");
  const container = timelineEl.querySelector(".single-column");

  const getLimitBasedOnContainer = () => {
    const scrollContainer = document.querySelector("#wrapwrap");
    const containerHeight = scrollContainer?.clientHeight || window.innerHeight;

    if (containerHeight >= 1200) return 18;
    if (containerHeight >= 900) return 12;
    if (containerHeight >= 700) return 9;
    return 6;
  };

  const limit = getLimitBasedOnContainer(); // Number of items to fetch per request
  let offset = limit; // Initial offset for loading data
  let isLoading = false; // Prevents multiple simultaneous requests
  let allLoaded = false; // Flags when all content has been loaded

  // --- Timeline animation logic (based on CodyHouse) ---
  class VerticalTimeline {
    constructor(element) {
      this.element = element;
      this.offset = 0.8;
      this.updateBlocks(); // Initialize references
      this.hideBlocks(); // Initial hide
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

    rpc(`/my2/children/${childId}/timeline-batch`, {offset, limit})
      .then((data) => {
        const html = data?.html || "";
        const hasMore = data?.has_more_records;

        if (html.trim()) {
          container.insertAdjacentHTML("beforeend", html);
          offset += limit;
          allLoaded = !hasMore;

          // After inserting new HTML, re-scan and animate
          timelineInstance.updateBlocks();
          timelineInstance.hideBlocks();
          timelineInstance.showBlocks();
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

  function checkIfMoreDataNeeded() {
    const scrollHeight = scrollParent.scrollHeight;
    const clientHeight = scrollParent.clientHeight;

    if (clientHeight <= scrollHeight + 100 && !allLoaded) {
      loadMoreData();
    }
  }

  // Initial check (in case first blocks are already visible)
  timelineInstance.showBlocks();
  checkIfMoreDataNeeded();
});
