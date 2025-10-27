document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.clear_letter_button_widget", function (require) {
        "use strict";

        const publicWidget = require("web.public.widget");

        publicWidget.registry.ClearLetterButtonWidget = publicWidget.Widget.extend({
            // The widget will attach to the form containing the button and input
            selector: '#new_letter_form',

            // Binds events to methods within the widget
            events: {
                'input #letter-input': '_onLetterInput',
                'click #clear-letter-button-container': '_onClearClick',
            },

            /**
             * The start method is part of the widget's lifecycle.
             * It runs once the widget is attached to the DOM.
             */
            start: function () {
                this._super.apply(this, arguments);
                // Run an initial check in case a draft is loaded with pre-existing text
                this._toggleClearButton();
            },

            // --- Custom Methods ---

            /**
             * Called every time the user types in the textarea.
             * @private
             */
            _onLetterInput: function () {
                this._toggleClearButton();
            },

/**
             * Called when the "Clear letter" button is clicked.
             * @private
             * @param {Event} ev - The click event.
             */
            _onClearClick: function (ev) {
                ev.preventDefault();
                // Use global '$' to find the input and clear it
                $('#letter-input').val('').trigger('input');
            },

            /**
             * The core logic to show or hide the button based on textarea content.
             * @private
             */
            _toggleClearButton: function () {
                // Use global '$' to find the input
                const hasText = $('#letter-input').val().trim().length > 0;
                // Use global '$' to find the button container and toggle its visibility
                $('#clear-letter-button-container').toggle(hasText);
            },
        });

        // This makes the widget available for use
        return publicWidget.registry.ClearLetterButtonWidget;
    });
});