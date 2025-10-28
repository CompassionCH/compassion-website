document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.clear_letter_button_widget", function (require) {
        "use strict";
        const { _t } = require("web.core");
        const publicWidget = require("web.public.widget");

        publicWidget.registry.ClearLetterButtonWidget = publicWidget.Widget.extend({
            // The widget will attach to the form containing the button and input
            selector: "#new_letter_form",

            // Binds events to methods within the widget
            events: {
                "input #letter-input": "_onUserInput",
                "click #clear-letter-button-container": "_onClearClick",
                // Add this new line for the template image click
                "click .template-image": "_onUserInput",
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
            _onUserInput: function () {
                this._toggleClearButton();
            },

            /**
             * Called when the "Clear letter" button is clicked.
             * @private
             * @param {Event} ev - The click event.
             */
            _onClearClick: function (ev) {
                ev.preventDefault();
                // Remove all written text from the textarea
                $("#letter-input").val("");

                // Remove the selected template image
                const img = document.getElementById("selected-template");
                if (img) {
                    img.remove();
                }
                // Restore the select template button label to default
                const button_label_element = document.getElementById("template-selection-label");
                if (button_label_element) {
                    button_label_element.textContent = _t("Select a template");
                }
                this._toggleClearButton();
            },

            /**
             * The core logic to show or hide the button based on textarea content.
             * @private
             */
            _toggleClearButton: function () {
                const hasText = $("#letter-input").val().trim().length > 0;
                const selectedTemplate = document.getElementById("selected-template") !== null;

                $("#clear-letter-button-container").toggle(hasText || selectedTemplate);
            },
        });

        // This makes the widget available for use
        return publicWidget.registry.ClearLetterButtonWidget;
    });
});
