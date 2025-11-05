/*
 * Provides a global fix to prevent a common Bootstrap modal error.
 * This widget overrides the 'compensateScrollbar' function, which can
 * cause the UI to crash when modals are open and the window is resized.
 *
 * This patch applies globally to all Bootstrap modals (.modal-dialog)
 * on the public website as long as this asset is loaded.
 *
 * If this fix is needed for other components, the 'selector'
 * in the widget can be extended to include them as well.
 *
 * Ticket: [T2733]
 * ------------------------------------------------------------------------------- */
odoo.define("my_compassion.my2_bootstrap_scrollbar_compensate_override", function (require) {
    "use strict";

    const publicWidget = require("web.public.widget");

    publicWidget.registry.ModalResizeFixWidget = publicWidget.Widget.extend({
        selector: ".modal-dialog",
        start: function () {
            this._super.apply(this, arguments);

            if (!window.jQuery) {
                console.error("ModalResizeFixWidget: Global jQuery not found.");
                return;
            }

            // Override Bootstrap's scrollbar compensation logic
            if (window.jQuery.fn.compensateScrollbar) {
                window.jQuery.fn.compensateScrollbar = function () {
                    return this;
                };
            }
        },
    });

    return publicWidget.registry.ModalResizeFixWidget;
});
