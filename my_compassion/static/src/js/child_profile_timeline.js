odoo.define("my_compassion.ChildTimelineInfiniteScrolling", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");
    const rpc = require("web.rpc");

    publicWidget.registry.ChildTimelineInfiniteScrolling = publicWidget.Widget.extend({
        selector: ".js-cd-timeline",

        /**
         * @override
         */
        start: function () {
            /*return this._super.apply(this, arguments).then(() => {
                setTimeout(() => this._initializeScroll(), 0);
            });*/
        },

        _initializeScroll: function () {
            if (!this.$el.length) return;

            this.offset = 9;
            this.limit = 9;
            this.childId = this.$el.data("child-id");
            this.isLoading = false;
            this.allLoaded = false;
            this._scrollInitialized = false;

            this.$loader = this.$("#timeline-loader");
            this.$container = this.$(".content-column");

            // For the scrolling to trigger, we attach the scrolling to the main container (wrapwrap)
            // as it is the main scrollable area, not the window due to a 100% height layout and an overflow auto.
            this._scrollHandler = this._onWindowScroll.bind(this);
            $("#wrapwrap").on("scroll.timeline", this._scrollHandler);
        },

        _onWindowScroll: function () {
            const scrollTop = $(window).scrollTop();
            const windowHeight = $(window).height();
            const documentHeight = $(document).height();

            // Trigger when user is within 100px of the bottom
            if (scrollTop + windowHeight >= documentHeight - 100) {
                this._loadMoreData();
            }
        },

        /**
         * @override
         */
        destroy: function () {
            $("#wrapwrap").off("scroll.timeline", this._scrollHandler);
            this._super.apply(this, arguments);
        },

        _loadMoreData: function () {
            if (this.isLoading || this.allLoaded) return;

            this.isLoading = true;
            this.$loader.show();

            rpc.query({
                route: `/my2/children/${this.childId}/timeline-batch`,
                params: {
                    offset: this.offset,
                    limit: this.limit,
                }
            }).then((data) => {
                if (data.trim()) {
                    this.$container.append(data);
                    this.offset += this.limit;
                } else {
                    this.allLoaded = true;
                }
            }).catch((error) => {
                console.error("RPC error while loading more data:", error);
            }).finally(() => {
                this.isLoading = false;
                this.$loader.hide();
            });
        },
    });
});