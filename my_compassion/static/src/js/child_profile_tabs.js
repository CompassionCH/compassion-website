document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.child_profile_tabs", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");

        publicWidget.registry.ChildProfileTabs = publicWidget.Widget.extend({
            selector: ".child-related-information",
            events: {
                "change #child-info-tabs-mobile": "_onMobileTabChange",
            },

            /**
             * @override
             */
            start: function () {
                // When a desktop tab is shown, update the mobile dropdown for consistency.
                // This is useful if a user resizes their browser window.
                this.$('#child-info-tabs a[data-toggle="tab"]').on("shown.bs.tab", (e) => {
                    const target = $(e.target).attr("href");
                    this.$("#child-info-tabs-mobile").val(target);
                });
                return this._super.apply(this, arguments);
            },

            //--------------------------------------------------------------------------
            // Handlers
            //--------------------------------------------------------------------------

            /**
             * When the mobile dropdown value changes, find the corresponding desktop
             * tab link and trigger a click to show the correct content pane.
             * @private
             * @param {Event} ev
             */
            _onMobileTabChange: function (ev) {
                const selectedTab = $(ev.currentTarget).val();
                this.$('#child-info-tabs a[href="' + selectedTab + '"]').tab("show");
            },
        });

        return publicWidget.registry.ChildProfileTabs;
    });
});
