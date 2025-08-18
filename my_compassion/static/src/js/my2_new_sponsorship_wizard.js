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
                "click .btn-next, .btn-previous, .btn-finish": "_onStepClick",
                "blur input[email]:visible": "_onEmailBlur",
                "blur input[phone_number]:visible": "_onPhoneNumberBlur",
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
             * Event handler for when the email input loses focus.
             */
            _onEmailBlur: function (ev) {
                this._validateEmail($(ev.currentTarget));
            },

            /**
             * Event handler for when the phone input loses focus.
             */
            _onPhoneNumberBlur: function (ev) {
                this._validatePhoneNumber($(ev.currentTarget));
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

                // validate email fields
                this.$("input[email]:visible").each(function (i, el) {
                    if (!this._validateEmail($(el))) {
                        isValid = false;
                    }
                }.bind(this));

                // validate phone number fields
                this.$("input[phone_number]:visible").each(function (i, el) {
                    if (!this._validatePhoneNumber($(el))) {
                        isValid = false;
                    }
                }.bind(this));

                return isValid;
            },

            /**
             * Validates a single email field for format.
             * @param {jQuery} $input - The jQuery object for the input field.
             * @returns {boolean}
             */
            _validateEmail: function($input) {
                if (!$input.val()) {
                    return true;
                }

                var emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

                $input.siblings('.input-invalid-hint').remove();
                $input.removeClass('is-invalid');

                if (!emailRegex.test($input.val())) {
                    $input.addClass("is-invalid");
                    var $errorHint = $(
                        '<div class="input-invalid-hint text-mid-orange tiny-text mb-1">Please enter a valid email address.</div>'
                    );
                    $input.before($errorHint);
                    return false;
                }
                return true;
            },

            /**
             * Validates a single phone number field for format.
             * @param {jQuery} $input - The jQuery object for the input field.
             * @returns {boolean}
             */
            _validatePhoneNumber: function($input) {
                if (!$input.val()) {
                    return true;
                }

                var phoneRegex = /^\+?(\d[\d\s-]{5,}\d)$/;

                $input.siblings('.input-invalid-hint').remove();
                $input.removeClass('is-invalid');

                if (!phoneRegex.test($input.val())) {
                    $input.addClass("is-invalid");
                    var $errorHint = $(
                        '<div class="input-invalid-hint text-mid-orange tiny-text mb-1">Please enter a valid phone number.</div>'
                    );
                    $input.before($errorHint);
                    return false;
                }
                return true;
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
