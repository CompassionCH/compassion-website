// Define a new Odoo module called 'my_compassion.toast_service'
odoo.define('my_compassion.toast_service', function (require) {
    "use strict";

    // Import the custom Toast notification widget
    const Toast = require("my_compassion.toast_notification");

    /**
     * A simple toast notification service that exposes
     * convenience methods for showing different types of notifications.
     */
    const ToastService = {
        /**
         * Show an informational toast message
         * @param {string} msg - The message body
         * @param {string} title - Optional title (defaults to 'Info')
         */
        info(msg, title = 'Info') {
            new Toast(null, {
                title,
                message: msg,
                type: 'info' // Bootstrap-style class for errorsz
            }).appendTo($('body')); // Appended to body to ensure visibility
        },

        /**
         * Show a success toast message
         * @param {string} msg - The message body
         * @param {string} title - Optional title (defaults to 'Success')
         */
        success(msg, title = 'Success') {
            new Toast(null, {
                title,
                message: msg,
                type: 'success'
            }).appendTo($('body'));
        },

        /**
         * Show a warning toast message
         * @param {string} msg - The message body
         * @param {string} title - Optional title (defaults to 'Warning')
         */
        warning(msg, title = 'Warning') {
            new Toast(null, {
                title,
                message: msg,
                type: 'warning'
            }).appendTo($('body'));
        },

        /**
         * Show an error toast message
         * @param {string} msg - The message body
         * @param {string} title - Optional title (defaults to 'Error')
         */
        error(msg, title = 'Error') {
            new Toast(null, {
                title,
                message: msg,
                type: 'danger'
            }).appendTo($('body'));
        }
    };

    // Return the ToastService so it can be used in other modules
    return ToastService;
});