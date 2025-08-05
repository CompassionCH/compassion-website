document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.new_sponsorship_wizard", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.NewSponsorshipWizard = publicWidget.Widget.extend({
            selector: ".new-sponsorship-wizard-form",
            events: {
                "click .btn-next, .btn-previous, .btn-finish": "_onStepClick",
            },

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
                                $(".new-sponsorship-wizard-form-content").html(data.html);
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

            /**
             * Validates required fields in the current step.
             * @returns {boolean} - True if valid, false otherwise.
             */
            _validateForm: function () {
                var isValid = true;
                // Remove previous error messages and styles
                this.$(".input-invalid-hint").remove();
                this.$("input.is-invalid").removeClass("is-invalid");

                // Find all required inputs within the current step that are visible
                this.$("input[required]:visible, select[required]:visible").each(function () {
                    var $input = $(this);
                    if (!$input.val()) {
                        isValid = false;
                        // Add the 'is-invalid' class
                        $input.addClass("is-invalid");

                        // Add a small text hint above the input field
                        var $errorHint = $(
                            '<div class="input-invalid-hint text-mid-orange tiny-text mb-1">This field is required.</div>'
                        );
                        var $select_container = $input.parent(".SelectComponent");

                        if ($select_container.length > 0) {
                            // If the input is a select component, place the hint before the container
                            $select_container.before($errorHint);
                        } else {
                            // Otherwise, it's a standard input, so place the hint before the input itself
                            $input.before($errorHint);
                        }
                    }
                });
                return isValid;
            },

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
