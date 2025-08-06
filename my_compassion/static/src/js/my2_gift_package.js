document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.gift_package", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");

        publicWidget.registry.GiftPackage = publicWidget.Widget.extend({
            selector: ".my2_gift_package_form",

            /**
             * @override
             */
            start: function () {
                return this._super.apply(this, arguments);
            },
        });

        return publicWidget.registry.GiftPackage;
    });
});