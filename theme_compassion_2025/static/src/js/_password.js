odoo.define("theme_compassion_2025.password", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    publicWidget.registry.Password = publicWidget.Widget.extend({
        template: "theme_compassion_2025.PasswordComponent",
        xmlDependencies: ["/theme_compassion_2025/static/src/xml/Password.xml"],

        events: {
            "click .password-show-toggle": "_onTogglePasswordVisibility",
            "touchend .password-show-toggle": "_onTogglePasswordVisibility",
        },

        /**
         * @override
         * @param {Widget} parent
         * @param {Object} options
         * @param {Boolean} [options.required=false] - Whether the input is mandatory.
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.required = (options && options.required) || false;
            this.inputName = (options && options.inputName) || "password";
        },

        /**
         * @override
         */
        start: function () {
            this.$passwordInput = this.$('input[type="password"]');
            this.$toggleIcon = this.$("i.password-show-toggle");

            return this._super.apply(this, arguments);
        },

        // --------------------------------------------------------------------------
        // Handlers
        // --------------------------------------------------------------------------

        /**
         * Toggles the visibility of the password in the input field and changes the icon.
         *
         * @private
         * @param {Event} ev
         */
        _onTogglePasswordVisibility: function (ev) {
            ev.preventDefault();

            const isPassword = this.$passwordInput.is('[type="password"]');
            this.$passwordInput.attr("type", isPassword ? "text" : "password");
            this.$toggleIcon.toggleClass("fa-eye-slash fa-eye");
        },
    });

    return publicWidget.registry.Password;
});
