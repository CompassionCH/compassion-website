odoo.define("theme_compassion_2025.event_banner", function (require) {
    "use strict";

    /**
     * Event Banner public widget
     * --------------------------
     * - Injects active event banners into the page (top of the first .container inside <main>)
     * - Animates open/close with CSS-driven transitions
     * - Persists _onClose in localStorage so a user won't see the same banner again
     *
     */

    const publicWidget = require("web.public.widget");
    const rpc = require("web.rpc");

    publicWidget.registry.EventBanner = publicWidget.Widget.extend({
        selector: "main",
        events: {
            "click .event-banner .action-close": "_onClose",
        },

        async start() {
            await this._super(...arguments);
            return this._loadAndRender();
        },

        async _loadAndRender() {
            const items = await rpc.query({
                route: "/my2/active-event-banners",
                params: {
                    current_page_route: window.location.pathname,
                },
            });

            if (!items || !items.length) {
                return;
            }

            const dismissedBanners = JSON.parse(localStorage.getItem("dismissedBanners") || "[]");
            const $container = $("main");

            items
                .slice()
                .reverse()
                .forEach((item) => {
                    if (!item || !item.html || dismissedBanners.includes(item.id)) {
                        return;
                    }
                    const $banner = $(item.html);

                    const $wrap = $('<div class="event-banner-wrap"></div>').append($banner);
                    $container.prepend($wrap);
                    const targetBannerHeight = $banner.outerHeight(true);

                    this._openAnimation($wrap, targetBannerHeight);
                });
        },

        _openAnimation($wrap, targetBannerHeight) {
            requestAnimationFrame(() => {
                $wrap.css("max-height", 0);
                $wrap.addClass("is-displayed");
                $wrap.css("max-height", targetBannerHeight + "px");

                const onEnd = (e) => {
                    const prop = e.originalEvent ? e.originalEvent.propertyName : e.propertyName;
                    if (e.target !== $wrap[0] || prop !== "max-height") {
                        return;
                    }
                    $wrap.off("transitionend", onEnd);
                    $wrap.css("max-height", "none");
                };

                $wrap.on("transitionend", onEnd);
            });
        },

        _dismiss(id) {
            const key = "dismissedBanners";
            const list = JSON.parse(localStorage.getItem(key) || "[]");
            if (!list.includes(id)) {
                list.push(id);
                localStorage.setItem(key, JSON.stringify(list));
            }
        },

        _onClose(ev) {
            ev.preventDefault();
            const $banner = $(ev.currentTarget).closest(".event-banner");
            const $wrap = $banner.closest(".event-banner-wrap");
            const id = $banner.data("id");

            this._closeAnimation($wrap, $banner);
            this._dismiss(id);
        },

        _closeAnimation($wrap, $banner) {
            if ($wrap.css("max-height") === "none") {
                $wrap.css("max-height", $banner.outerHeight(true) + "px");
            }

            requestAnimationFrame(() => {
                $wrap
                    .removeClass("is-displayed")
                    .css("max-height", 0)
                    .one("transitionend", () => $wrap.remove());
            });
        },
    });

    return publicWidget.registry.EventBanner;
});
