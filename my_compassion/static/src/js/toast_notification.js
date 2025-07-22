// Define a new module in Odoo called 'my_compassion.toast_notification'
odoo.define('my_compassion.toast_notification', function (require) {
    "use strict";

    // Import the base Widget class from Odoo's web framework
    const Widget = require('web.Widget');

    // Create a new widget class by extending the base Widget
    const ToastNotification = Widget.extend({
        // Define the QWeb template to use for rendering this widget
        // This template should be defined in the XML file specified in xmlDependencies
        // The template will be used to create the HTML structure of the toast notification
        // See also the my2_assets.xml file for the template definition
        template: 'my_compassion.toast_notification_component',

        // Include the XML file where the template is defined
        xmlDependencies: ['/my_compassion/static/src/xml/toast_notification.xml'],

        /**
         * Widget constructor
         * @param {Widget} parent - the parent widget (can be null)
         * @param {Object} options - configuration object for the toast
         */
        init: function (parent, options) {
            // Set default values if not provided
            this.message = options.message || "Default message";
            this.title = options.title || "Notification";
            this.type = options.type || "info";  // Defines the style: success, danger, info, etc.

            // Call the parent constructor
            this._super(parent, options);
        },

        /**
         * Lifecycle hook that runs after the widget is inserted into the DOM
         */
        start: function () {
            // Dismiss when the close button is clicked
            this.$('.close').on('click', () => this.destroy());

            // The average reading time for a toast is around 5 seconds + 1 second per 120 characters
            // so, automatically remove the toast after 6 seconds
            setTimeout(() => this.destroy(), 6000);

            // Call the parent start method
            return this._super.apply(this, arguments);
        },
    });

    // Export the widget class so it can be used elsewhere
    return ToastNotification;
});
