/** @odoo-module **/

/**
 * Responsive Child Profile Tabs Widget
 * ------------------------------------
 * Synchronizes a mobile dropdown selector with the Bootstrap desktop tab nav
 * on a child's profile page: a desktop tab change updates the mobile dropdown,
 * and a mobile dropdown change activates the matching desktop tab.
 */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ChildProfileTabs = publicWidget.Widget.extend({
    selector: ".child-related-information",
    events: {
        "change #child-info-tabs-mobile": "_onMobileTabChange",
    },

    /**
     * @override
     */
    start: function () {
        // When a desktop tab is shown, mirror it into the mobile dropdown so the
        // two stay consistent across a resize.
        this.$('#child-info-tabs a[data-bs-toggle="tab"]').on("shown.bs.tab", (e) => {
            const target = $(e.target).attr("href");
            this.$("#child-info-tabs-mobile").val(target);
        });
        return this._super.apply(this, arguments);
    },

    /**
     * Activate the desktop tab matching the mobile dropdown selection.
     * @private
     * @param {Event} ev
     */
    _onMobileTabChange: function (ev) {
        const selectedTab = $(ev.currentTarget).val();
        const tabLink = this.el.querySelector(`#child-info-tabs a[href="${selectedTab}"]`);
        if (tabLink) {
            window.Tab.getOrCreateInstance(tabLink).show();
        }
    },
});
