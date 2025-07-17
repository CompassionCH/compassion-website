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
            this.offset = 9; // Start with the first page already loaded
            this.limit = 9;
            this.childId = this.$el.data("child-id");
            this.isLoading = false;
            this.allLoaded = false;

            this.$loader = this.$("#timeline-loader");
            this.$container = this.$(".content-column");

            console.log('ChildTimelineInfiniteScrolling has started');

            // Bind scroll to window manually
            this._scrollHandler = this._onWindowScroll.bind(this);
            $(window).on("scroll.timeline", this._scrollHandler);

            return this._super.apply(this, arguments);
        },

        _onWindowScroll: function () {
            const loaderTop = this.$loader.offset().top;
            const windowBottom = $(window).scrollTop() + $(window).height();

            if (windowBottom >= loaderTop - 50) {
                this._loadMoreData();
            }
        },

        /**
         * @override
         */
        destroy: function () {
            // Important to clean up the event listener to prevent memory leaks
            $(window).off("scroll.timeline", this._scrollHandler);
            this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _loadMoreData: function () {
            console.log('ChildTimelineInfiniteScrolling loads more data');
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

