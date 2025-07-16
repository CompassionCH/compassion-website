document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.child_profile_timeline", function (require) {
        "use strict";

        const publicWidget = require("web.public.widget");
        const rpc = require("web.rpc");

        publicWidget.registry.ChildTimeline = publicWidget.Widget.extend({
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

                const scrollEl = this.$el.closest(".o_content, .main-content, body");

                // Listen to scroll events on the window
                scrollEl.on("scroll.timeline", this._onScroll.bind(this));

                return this._super.apply(this, arguments);
            },

            /**
             * @override
             */
            destroy: function () {
                // Important to clean up the event listener to prevent memory leaks
                $(window).off("scroll.timeline");
                this._super.apply(this, arguments);
            },

            //--------------------------------------------------------------------------
            // Handlers
            //--------------------------------------------------------------------------

            _onScroll: function () {
                // Do nothing if we are already loading or if all items have been loaded
                if (this.isLoading || this.allLoaded) {
                    return;
                }
                const loaderTop = this.$loader.offset().top;
                const windowBottom = $(window).scrollTop() + $(window).height();

                if (windowBottom >= loaderTop - 50) {
                    this.isLoading = true;
                    this.$loader.show();

                    rpc.query({
                        route: `/my2/children/${this.childId}/timeline-batch?offset=${this.offset}&limit=${this.limit}`,
                    }).then((data) => {
                        if (data.trim()) {
                            this.$container.append(data);
                            this.offset += this.limit;
                        } else {
                            this.allLoaded = true; // No more data to load
                        }

                        this.isLoading = false;
                        this.$loader.hide();
                    });
                }
            },
        });
        return publicWidget.registry.ChildTimeline;
    });
});
