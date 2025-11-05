odoo.define("my_compassion.my2_prevent_modal_resize_error", function (require) {
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
