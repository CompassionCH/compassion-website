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
        var ajax = require("web.ajax");

        publicWidget.registry.NewSponsorshipWizard = publicWidget.Widget.extend({
            selector: ".new-sponsorship-wizard-form",
            events: {
                "click .btn-next, .btn-previous": "_onStepClick",
                "click .btn-sponsor": "_onSponsorClick",
                "change .wap-contribute": "_onWAPContributeChange",
                "change .suggested-amount": "_onAmountChange",
                "change #payment_method": "_onPaymentMethodChange",
                "click #start_ebill_workflow_btn": "_onStartEbillWorkflow",
                "click #ebill_content_container button[type='submit']": "_onEbillFormSubmit",
                "click #ebill_content_container a[type='submit']": "_onEbillFormSubmit",
            },
            _eBill: { has_contract: false, partner: null, contract: null },

            /**
             * @override
             */
            start: function () {
                this._super.apply(this, arguments);

                this._updateUI();
                this._onPaymentMethodChange();
                this._initEbillState();
            },

            /**
             * Checks if user has already an ebill contract.
             * @private
             */
            _initEbillState: function () {
                return rpc
                    .query({
                        route: "/ebill/current-user/contract",
                        params: {},
                    })
                    .then((eBillInfoOfCurrentUser) => {
                        this._eBill = eBillInfoOfCurrentUser;
                    })
                    .catch((err) => {
                        console.warn("Could not check existing eBill contract:", err);
                    });
            },

            /**
             * Handles the change event on the payment method dropdown.
             * @private
             */
            _onPaymentMethodChange: function () {
                const selectedText = this.$("#payment_method option:selected").text();
                const isEBill = selectedText.includes("eBill");

                if (isEBill) {
                    if (!this._eBill.has_contract) {
                        this.$("#ebill_setup_container").toggleClass("d-none", false);
                        this.$("#finishButton").prop("disabled", true);
                    }
                } else {
                    this.$("#ebill_setup_container").toggleClass("d-none", true);
                    this.$("#finishButton").prop("disabled", false);
                }
            },

            /**
             * Starts the E-Bill workflow when the "Set up" button is clicked.
             * @private
             * @param {Event} ev
             */
            _onStartEbillWorkflow: function (ev) {
                ev.preventDefault();

                const params = {
                    is_integrated: true,
                    email: this._eBill.partner?.email,
                };

                ajax.post("/ebill/subscribe", params)
                    .then((html) => {
                        this.$("#ebill_setup_container").show();
                        this.$("#ebill_content_container").html(html);
                        this.$("#finishButton").prop("disabled", true);
                    })
                    .catch(console.error);
            },
            /**
             * Intercepts form submissions inside the E-Bill modal and handles them via rpc.
             * @private
             * @param {Event} ev
             */
            _onEbillFormSubmit: function (ev) {
                const form = ev.delegateTarget;
                const noValidationNeeded = $(ev.currentTarget).is("[formnovalidate]");

                if (!form.checkValidity() && !noValidationNeeded) {
                    form.reportValidity();
                    return;
                }

                ev.preventDefault();
                ev.stopPropagation();

                const action = ev.currentTarget.dataset.action;

                const params = {
                    is_integrated: true,
                };

                if (!action) {
                    console.error("The clicked button is missing a 'data-action' attribute.");
                    return;
                } else if (action === "/ebill/validate") {
                    params.email = this.$("#email_input").val() ?? this.$("#email").val();
                } else if (action === "/ebill/confirm") {
                    params.validation_code = this.$("#validation_code_input").val();
                    params.token = this.$("#token").val();
                    params.email = this.$("#email").val();
                }

                ajax.post(action, params)
                    .then((html) => {
                        this.$("#ebill_content_container").html(html);
                        const doneSuccessfully = this.$("#ebill_content_container #ebill-success-marker").length > 0;
                        if (doneSuccessfully) {
                            this.$("#finishButton").prop("disabled", false);
                        }
                    })
                    .catch(console.error);
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

            /**
             * Handles the change event for the Write&Pray contribute radio buttons.
             * @private
             * @param {Event} ev The jQuery event object.
             */
            _onWAPContributeChange: function (ev) {
                this._updateUI("fast");
            },

            /**
             * Handles the change event for the suggested amounts radio buttons.
             * @private
             * @param {Event} ev The jQuery event object.
             */
            _onAmountChange: function (ev) {
                this._updateUI("fast");
            },

            /**
             * Updates UI
             * @private
             * @param speed
             */
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
