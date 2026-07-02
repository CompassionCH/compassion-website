/** @odoo-module **/

/**
 * Event Banner Widget
 *
 * publicWidget mounted on `main`. On page load, fetches active event banners
 * from the /my2/active-event-banners endpoint (passing the current pathname),
 * filters out banners the user has already dismissed (stored in localStorage
 * under the key "dismissedBanners"), injects each remaining banner as a
 * `<div class="event-banner-wrap">` prepended to `<main>`, and animates it
 * open with a CSS max-height transition.
 *
 * Dismissal: clicking `.action-close` inside `.event-banner` triggers a
 * reverse max-height transition and stores the banner id in localStorage so
 * it is not shown again in subsequent page loads.
 *
 * Graceful degradation: if the fetch fails (endpoint not available), the
 * error is caught and the page renders without banners.
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

const DISMISSED_KEY = "dismissedBanners";

publicWidget.registry.themeCompassionEventBanner = publicWidget.Widget.extend({
  selector: "main",
  events: {
    "click .event-banner .action-close": "_onClose",
  },

  async start() {
    await this._super(...arguments);
    return this._loadAndRender();
  },

  async _loadAndRender() {
    let items = null;
    try {
      items = await rpc("/my2/active-event-banners", {
        current_page_route: window.location.pathname,
      });
    } catch {
      return;
    }

    if (!items || !items.length) {
      return;
    }

    const dismissedBanners = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");

    items
      .slice()
      .reverse()
      .forEach((item) => {
        if (!item || !item.html || dismissedBanners.includes(String(item.id))) {
          return;
        }
        const template = document.createElement("template");
        template.innerHTML = item.html;
        const bannerEl = template.content.firstElementChild;
        const wrapEl = document.createElement("div");
        wrapEl.className = "event-banner-wrap";
        wrapEl.appendChild(bannerEl);
        this.el.prepend(wrapEl);
        const targetBannerHeight = bannerEl.getBoundingClientRect().height;
        this._openAnimation(wrapEl, targetBannerHeight);
      });
  },

  _openAnimation(wrapEl, targetBannerHeight) {
    requestAnimationFrame(() => {
      wrapEl.style.maxHeight = "0";
      wrapEl.classList.add("is-displayed");
      wrapEl.style.maxHeight = targetBannerHeight + "px";

      const onEnd = (e) => {
        if (e.target !== wrapEl || e.propertyName !== "max-height") {
          return;
        }
        wrapEl.removeEventListener("transitionend", onEnd);
        wrapEl.style.maxHeight = "none";
      };

      wrapEl.addEventListener("transitionend", onEnd);
    });
  },

  _dismiss(id) {
    const list = JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]");
    const idStr = String(id);
    if (!list.includes(idStr)) {
      list.push(idStr);
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(list));
    }
  },

  _onClose(ev) {
    ev.preventDefault();
    const bannerEl = ev.currentTarget.closest(".event-banner");
    const wrapEl = bannerEl && bannerEl.closest(".event-banner-wrap");
    const id = bannerEl && bannerEl.dataset.id;

    if (wrapEl && bannerEl) {
      this._closeAnimation(wrapEl, bannerEl);
    }
    if (id !== undefined && id !== null) {
      this._dismiss(id);
    }
  },

  _closeAnimation(wrapEl, bannerEl) {
    if (wrapEl.style.maxHeight === "none") {
      wrapEl.style.maxHeight = bannerEl.getBoundingClientRect().height + "px";
    }

    requestAnimationFrame(() => {
      wrapEl.classList.remove("is-displayed");
      wrapEl.style.maxHeight = "0";
      wrapEl.addEventListener("transitionend", () => wrapEl.remove(), {
        once: true,
      });
    });
  },
});

export default publicWidget.registry.themeCompassionEventBanner;
