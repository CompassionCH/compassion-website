/*
 * Handle the new sponsorship wizard. It handles users actions such as
 * step navigation (next/previous), form validation, dynamic content
 * loading, and communication with the server via API calls to process the
 * sponsorship application.
 *
 * Used in /templates/pages/my2_new_sponsorship_wizard.xml
 * ------------------------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.new_sponsorship_wizard", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.NewSponsorshipWizard = publicWidget.Widget.extend({
            selector: ".new-sponsorship-wizard-form",
            events: {
                "click .btn-next, .btn-previous, .btn-finish": "_onStepClick"
            },

            // ====================================================================
            // Event Handlers
            // ====================================================================

            /**
             * Handles the click on "Next" or "Previous" buttons.
             * @param {Event} ev
             */
            _onStepClick: function (ev) {
                ev.preventDefault();

                var action = $(ev.currentTarget).attr("name"); // 'next', 'previous' or finish

                // Don't validate when moving backwards
                if (action !== "previous" && !this._validateForm()) {
                    return; // Stop execution if validation fails
                }

                // Prevent double clicks
                this.$(".btn").prop("disabled", true);

                // Submit the form and return if action is finish
                if (action === "finish") {
                    $(".new-sponsorship-wizard-form").submit();
                    return;
                }

                // Serialize form and add action
                var formData = this.$el.serializeArray();
                formData.push({ name: "action", value: action });

                // Use RPC to call the controller method
                rpc.query({
                    route: "/my2/new-sponsorship/step",
                    params: this._serializeForm(formData),
                })
                    .then(
                        function (data) {
                            // Replace the form's inner content with the new step's HTML
                            if (data.html) {
                            /*
                                $(".new-sponsorship-wizard-form-content").html(data.html);
                                $("html, body").animate({ scrollTop: 0 }, "slow");*/
                                var $newContent = $(data.html);
                                this.$(".new-sponsorship-wizard-form-content").empty().append($newContent);

                                // DIES IST DER ENTSCHEIDENDE SCHRITT:
                                // Odoo anweisen, alle Widgets innerhalb des neuen Inhalts zu starten.
                                this.trigger_up('widgets_start_request', {
                                    $target: $newContent
                                });

                                // Scrolle nach oben
                                $("html, body").animate({ scrollTop: 0 }, "slow");
                            }
                            // Re-enable buttons
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    )
                    .guardedCatch(
                        function () {
                            // Re-enable buttons also in case of error
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    );
            },

            // ====================================================================
            // Validation Logic
            // ====================================================================

            /**
             * Validates required fields in the current step.
             * @returns {boolean} - True if valid, false otherwise.
             */
             _validateForm: function () {
                var isValid = true;

                // Finde alle FormField-Komponenten im aktuellen Schritt
                this.$(".form-field-component:visible").each(function () {
                    // Odoo hängt die Widget-Instanz an die DOM-Element-Daten an
                    var fieldWidget = $(this).data("widget");

                    // Rufe die öffentliche validate() Methode unseres neuen Widgets auf
                    if (fieldWidget && !fieldWidget.validate()) {
                        isValid = false;
                    }
                });

                return isValid;
            },
            // ====================================================================
            // Helper Functions
            // ====================================================================

            /**
             * Helper to convert form data array to a key-value object.
             * @param {Array} formData
             * @returns {Object}
             */
            _serializeForm: function (formData) {
                var obj = {};
                for (const field of formData) {
                    obj[field.name] = field.value;
                }
                return obj;
            },
        });

        return publicWidget.registry.NewSponsorshipWizard;
    });
});
