    odoo.define('my_compassion.my2_prevent_modal_resize_error', function (require) {
        "use strict";

        const publicWidget = require("web.public.widget");

        publicWidget.registry.TemplateSelectionWidget = publicWidget.Widget.extend({
            selector: ".modal-dialog",
            start: function () {

                this._super.apply(this, arguments);

                if (!window.jQuery) {
                    console.error("TemplateSelectionWidget: Global jQuery not found.");
                    return;
                }

                // override bootstrap scroll event method
                if (window.jQuery.fn.compensateScrollbar) {
                    window.jQuery.fn.compensateScrollbar = function () {
                        return this;
                    };
                }

            },
        });

        return publicWidget.registry.TemplateSelectionWidget;
    });
