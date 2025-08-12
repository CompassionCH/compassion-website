document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.login", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");

        publicWidget.registry.Login = publicWidget.Widget.extend({
            selector: ".my2-login-form",

            /**
             * @override
             */
            start: function () {
                // Create password element
                var passwordElement = this.$(".password");
                this.password = new publicWidget.registry.Password(this);
                this.password.replace(passwordElement);

                return this._super.apply(this, arguments);
            },
        });

        return publicWidget.registry.Sponsorships;
    });
});
