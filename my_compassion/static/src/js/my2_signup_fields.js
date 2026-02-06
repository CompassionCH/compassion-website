document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.signup", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");

        publicWidget.registry.SignupFields = publicWidget.Widget.extend({
            selector: ".my2-signup-fields",

            /**
             * @override
             */
            start: function () {
                // Create password elements

                for (var passwordElement of this.$(".password")) {
                    var $passwordElement = $(passwordElement);
                    var password = new publicWidget.registry.Password(this, {
                        inputName: $passwordElement.data("name"),
                    });
                    password.replace($passwordElement);
                }

                return this._super.apply(this, arguments);
            },
        });

        return publicWidget.registry.SignupFields;
    });
});
