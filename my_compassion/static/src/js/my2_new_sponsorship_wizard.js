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
            _hasAlreadyEbillContract: false,
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

            /**
             * @override
             */
            start: function () {
                this._super.apply(this, arguments);
                this._updateUI();
                this._onPaymentMethodChange();
                this._initEbillState();
            },

            // ... (keep all your existing methods like _onStepClick, _validateForm, etc.)
            /**
             * Checks if user has already an ebill contract.
             * @private
             */
            _initEbillState: function () {
                return rpc.query({
                    route: "/ebill/current-user/contract",
                    params: {},
                })
                .then((res) => (res && res.has_contract))
                .then((exists) => this._hasEbillContract = exists)
                .catch((err) => {
                    console.warn("Could not check existing eBill contract:", err);
                });
            },

            /**
             * Handles the change event on the payment method dropdown.
             * @private
             */
            _onPaymentMethodChange: function () {
                const selectedText = this.$('#payment_method option:selected').text();
                const isEbill = selectedText.includes('eBill');



                if (isEbill && !this._hasAlreadyEbillContract) {
                    this.$('#ebill_setup_container').toggle(isEbill);
                    this.$('#finishButton').prop('disabled', true);
                } else {
                    this.$('#finishButton').prop('disabled', false);
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
                    params: { is_integrated: true },
                }).then(data => {
                    this.$('#ebill_setup_container').show();
                    this.$('#ebill_content_container').html(data.html);
                    this.$('#finishButton').prop('disabled', true);
                }).catch(console.error);
            },
            /**
             * Intercepts form submissions inside the E-Bill modal and handles them via AJAX.
             * @private
             * @param {Event} ev
             */
            _onEbillFormSubmit: function (ev) {
                const form = ev.delegateTarget; // das <form> Element
                // Native HTML5 Validierung
                if (!form.checkValidity()) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    form.reportValidity(); // zeigt Browser-Hinweise an
                    return;
                }

                ev.preventDefault(); // ab hier AJAX übernehmen
                ev.stopPropagation();

                const action = ev.currentTarget.dataset.action;

                let email;
                let validationCode;
                let token;
                if (!action) {
                    console.error("The clicked button is missing a 'data-action' attribute.");
                    return;
                }   else if (action === "/ebill/validate"){
                    email =  this.$('#email_input').val() ?? this.$('#email').val();
                } else if (action === "/ebill/confirm") {
                    validationCode = this.$('#validation_code_input').val();
                    token = this.$('#token').val();
                    email = this.$('#email').val();
                }

                const params = {
                    is_integrated: true,
                    email: email,
                    validation_code: validationCode,
                    token: token
                };

                rpc.query({
                    route: action,
                    params: params,
                }).then(data => {
                   this.$('#ebill_content_container').html(data.html);
                }).catch(console.error);
            },

            _onStepClick: function (ev) {
                ev.preventDefault();

                const action = $(ev.currentTarget).data("action"); // 'next', 'previous'
                const sponsorship_type = $(ev.currentTarget).data("sponsorship-type"); // 'standard', 'write_and_pray'

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