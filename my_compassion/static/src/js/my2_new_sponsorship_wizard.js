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
                "click .btn-next, .btn-previous": "_onStepClick",
                "click .btn-sponsor": "_onSponsorClick",
                "change .wap-contribute": "_onWAPContributeChange",
                "change .suggested-amount": "_onAmountChange",
                // START: E-BILL EVENTS
                "change #payment_method": "_onPaymentMethodChange",
                "click #start_ebill_workflow_btn": "_onStartEbillWorkflow",
                "submit #ebill_workflow_modal form": "_onEbillFormSubmit",
                // END: E-BILL EVENTS
            },

            /**
             * @override
             */
            start: function () {
                this._super.apply(this, arguments);
                this._updateUI();
                // Check initial state in case the user comes back to this step
                this._onPaymentMethodChange();
            },

            // ... (keep all your existing methods like _onStepClick, _validateForm, etc.)

            /**
             * Handles the change event on the payment method dropdown.
             * @private
             */
            _onPaymentMethodChange: function () {
                console.log("changed")
                const selectedText = this.$('#payment_method option:selected').text();
                const isEbill = selectedText.includes('eBill');

                this.$('#ebill_setup_container').toggle(isEbill);

                if (isEbill) {
                    this.$('.btn-next').prop('disabled', true);
                } else {
                    this.$('.btn-next').prop('disabled', false);
                }
            },

            /**
             * Starts the E-Bill workflow when the "Set up" button is clicked.
             * @private
             * @param {Event} ev
             */
            _onStartEbillWorkflow: function (ev) {
                ev.preventDefault();
                // Ersten Schritt (Subscribe) per JSON holen
                rpc.query({
                    route: '/ebill/subscribe',
                    params: { is_ajax: true },
                }).then(data => {
                    // In den Container schreiben
                    this.$('#ebill_setup_container').show();
                    this.$('#ebill_modal_content').html(data.html); // REPLACE, nicht append
                    // "Finish" Button blockieren bis Erfolg
                    this.$('.btn-next').prop('disabled', true);
                }).catch(console.error);
            },
            /**
             * Intercepts form submissions inside the E-Bill modal and handles them via AJAX.
             * @private
             * @param {Event} ev
             */
            _onEbillFormSubmit: function (ev) {
                ev.preventDefault();
                const $form = $(ev.currentTarget);
                const action = $form.attr('action');
                const formData = $form.serializeArray();
                formData.push({ name: 'is_ajax', value: '1' }); // Ensure the ajax flag is sent

                // Show a loading indicator in the modal
                this.$('#ebill_modal_content').html('<div class="text-center"><i class="fa fa-spinner fa-spin"/> Loading...</div>');

                rpc.query({
                    route: action,
                    params: this._serializeForm(formData),
                }).then(data => {
                    if (data.success) {
                        // Workflow is complete and successful!
                        this.$('#ebill_workflow_modal').modal('hide');
                        this.$('#ebill_setup_container .alert-info').hide(); // Hide the initial message and button
                        this.$('#ebill_success_message').show(); // Show success message
                        // Enable the main Finish button
                        this.$('.btn-next').prop('disabled', false);
                    } else if (data.html) {
                        // Load the next step's HTML into the modal
                        this.$('#ebill_modal_content').html(data.html);
                    }
                }).guardedCatch(error => {
                    // Handle validation errors or other failures from the backend
                    const errorMessage = error.data.message || 'An error occurred. Please try again.';
                    const $errorDiv = $('<div class="alert alert-danger"/>').text(errorMessage);
                    this.$('#ebill_modal_content').find('.alert-danger').remove();
                    this.$('#ebill_modal_content').prepend($errorDiv);
                     // It might be good to reload the previous step here if possible, or provide a retry button.
                });
            },

            _onStepClick: function (ev) {
                ev.preventDefault();

                const action = $(ev.currentTarget).data("action"); // 'next', 'previous'
                const sponsorship_type = $(ev.currentTarget).data("sponsorship-type"); // 'standard', 'write_and_pray'

                // Don't validate when moving backwards
                if (action !== "previous" && !this._validateForm()) {
                    return; // Stop execution if validation fails
                }

                // Check age for Write&Pray
                if (action !== "previous" && sponsorship_type == "write_and_pray") {
                    const dateThreshold = new Date();
                    dateThreshold.setFullYear(dateThreshold.getFullYear() - 25);
                    const birthdate = new Date(this.$("#birthdate").val());
                    if (birthdate < dateThreshold) {
                        this.$("#wap-age-modal").modal("show");
                        return;
                    }
                }

                // Prevent double clicks
                this.$(".btn").prop("disabled", true);

                // Serialize form and add action
                var formData = this.$el.serializeArray();
                formData.push({ name: "action", value: action });
                formData.push({ name: "sponsorship_type", value: sponsorship_type });

                // Use RPC to call the controller method
                rpc.query({
                    route: "/my2/new-sponsorship/step",
                    params: this._serializeForm(formData),
                })
                    .then(
                        function (data) {
                            // Replace the form's inner content with the new step's HTML
                            if (data.html) {
                                // Destroy modal
                                const modal = this.$("#wap-age-modal");
                                if (modal) {
                                    $(".modal-backdrop").remove();
                                    $("body").removeClass("modal-open");
                                }

                                this.$(".new-sponsorship-wizard-form-content").html(data.html);
                                $("html, body").animate({ scrollTop: 0 }, "slow");
                            }
                            if (data.finish) {
                                this.$el.submit();
                            } else {
                                // Re-enable buttons
                                this.$(".btn").prop("disabled", false);
                                this._updateUI();
                            }
                        }.bind(this)
                    )
                    .guardedCatch(
                        function () {
                            // Re-enable buttons also in case of error
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    );
            },
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
            _serializeForm: function (formData) {
                var obj = {};
                for (const field of formData) {
                    obj[field.name] = field.value;
                }
                return obj;
            },
            _onWAPContributeChange: function (ev) {
                this._updateUI("fast");
            },
            _onAmountChange: function (ev) {
                this._updateUI("fast");
            },
            _updateUI: function (speed = 0) {
                if (this.$(".wap-contribute:checked").val() === "true") {
                    this.$("#wap-contribution-amount").slideDown(speed);
                } else {
                    this.$("#wap-contribution-amount").slideUp(speed);
                }

                if (this.$(".suggested-amount:checked").val() === "custom") {
                    this.$(".custom-amount-field").slideDown(speed);
                } else {
                    this.$(".custom-amount-field").slideUp(speed);
                }
            },
        });
        return publicWidget.registry.NewSponsorshipWizard;
    });
});