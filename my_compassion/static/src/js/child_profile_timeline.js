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
            this.offset = 9;
            this.limit = 9;
            this.childId = this.$el.data("child-id");
            this.isLoading = false;
            this.allLoaded = false;
            this._scrollInitialized = false;

            this.$loader = this.$("#timeline-loader");
            this.$container = this.$(".content-column");
            const widgetThis = this;

            console.log("ChildTimelineInfiniteScrolling has started");

            $( document ).ready(function() {
                widgetThis._scrollHandler = widgetThis._onWindowScroll.bind(widgetThis);
                $(window).on("scroll.timeline", widgetThis._scrollHandler);
                console.log(widgetThis);
            });

            return this._super.apply(this, arguments);
        },

        _onWindowScroll: function () {
            console.log("ChildTimelineInfiniteScrolling _onWindowScroll");

            const timelineBottom = this.$el.offset().top + this.$el.outerHeight();
            const windowBottom = $(window).scrollTop() + $(window).height();

            if (windowBottom >= timelineBottom - 50) {
                this._loadMoreData();
            }
        },

        /**
         * @override
         */
        destroy: function () {
            $(window).off("scroll.timeline", this._scrollHandler);
            this._super.apply(this, arguments);
        },

        _loadMoreData: function () {
            console.log("ChildTimelineInfiniteScrolling loads more data");

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

                this.isLoading = false;
                this.$loader.hide();
            });
        },
    });
});