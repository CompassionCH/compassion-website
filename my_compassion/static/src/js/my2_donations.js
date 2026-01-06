odoo.define("my_compassion.my2_donations", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");
    var core = require("web.core");
    var QWeb = core.qweb;
    const ToastService = require("my_compassion.toast_service");
    var _t = core._t;
    var ajax = require('web.ajax');

    publicWidget.registry.My2Donations = publicWidget.Widget.extend({
        selector: ".my2-donations-page",

        // Load Client-Side QWeb Templates
        xmlDependencies: ["/my_compassion/static/src/xml/my2_payment_method_templates.xml"],

        events: {
            // Custom events dispatched from the DOM (e.g. from my2_sponsorships_group_card.xml)
            open_payment_method_update: "_onOpenUpdateModal",
            open_payment_method_change: "_onOpenChangeModal",
            open_payment_method_add: "_onOpenAddModal",

            // UI Interaction events
            "click #btn_save_payment_method": "_onSavePaymentMethod",
            'change input[name="payment_method_selection"]': "_onMethodSelectionChange",
            "click #history_pager_prev, #history_pager_next": "_onPagerClick",

            'change #new_method_type': '_onAddMethodChange',
            'click #postfinance-submit-btn': '_onSubmitPostFinance'
        },


        /**
         * Widget Initialization
         */
        start: function () {
            var self = this;

            // 1. Initialize Local State
            // Read the initial list of payment methods passed from the backend template
            var $container = this.$("#my_sponsorships_container");
            this.paymentMethods = $container.data("payment-methods") || [];

            // 2. Global Bindings (Cleanup & Modal behaviors)
            this._onModalHiddenGlobalBound = this._onModalHiddenGlobal.bind(this);
            this._onMethodSelectionChangeBound = this._onMethodSelectionChange.bind(this);

            $("body").on("hidden.bs.modal", ".modal", this._onModalHiddenGlobalBound);
            // We bind change to body to catch inputs inside dynamically rendered modals
            $("body").on("change", 'input[name="payment_method_selection"]', this._onMethodSelectionChangeBound);

            // 3. Check for URL flash messages (e.g. after redirects)
            this._checkAddPaymentMethod();

            return this._super.apply(this, arguments);
        },

        destroy: function () {
            if (this._onModalHiddenGlobalBound) {
                $("body").off("hidden.bs.modal", ".modal", this._onModalHiddenGlobalBound);
            }
            if (this._onMethodSelectionChangeBound) {
                $("body").off("change", 'input[name="payment_method_selection"]', this._onMethodSelectionChangeBound);
            }
            this._super.apply(this, arguments);
        },

        // -------------------------------------------------------------------------
        // MODAL OPEN HANDLERS
        // -------------------------------------------------------------------------

        /**
         * Opens the "Change" modal (Moving a contract to a different group/method)
         */
        _onOpenChangeModal: function (ev) {
            ev.stopPropagation();
            // detail contains: { contract_id, group_id, child_name } passed via detail_js
            var detail = ev.detail || {};
            var $container = this.$("#my_sponsorships_container");
            this.paymentMethods = $container.data("payment-methods") || [];
            var $modal = $("#payment_method_selector_modal_change");

            // Update Description
            $modal
                .find("#modal_description")
                .text(
                    _.str.sprintf(
                        _t("Change your payment method for %s."),
                        detail.child_name || _t("your sponsored child")
                    )
                );

            // Store context
            $modal.data("contract-id", detail.contract_id);

            // Render the list of available methods
            // We pass the current group_id to highlight the currently active method
            this._renderPaymentMethodsList($modal, detail.group_id, "#modal_container");

            $modal.modal("show");
        },

        /**
         * Opens the "Update" modal (Editing the current group's details or merging)
         */
        _onOpenUpdateModal: function (ev) {
            ev.stopPropagation();
            var detail = ev.detail || {};
            // detail contains: { group_id, method_info }

            var $modal = $("#payment_method_selector_modal_update");
            $modal.data("group-id", detail.group_id);

            // 1. Render the "Update Current Details" Form
            // We reuse the client-side QWeb template for the form
            // Note: detail.method_info comes from the data-attributes we setup in the template
            var formHtml = QWeb.render("my_compassion.PaymentMethodUpdateAccordion", detail.method_info || {});
            $modal.find("#modal_container").empty().html(formHtml);

            // 2. Render the "Switch" list in the accordion
            this._renderPaymentMethodsList($modal, detail.group_id, "#payment_methods_switch_container");

            $modal.modal("show");
        },

        /**
         * Opens the "Add" modal and initializes Online Methods
         */
        _onOpenAddModal: function (ev) {
            if (ev) ev.stopPropagation();
            $("#payment_method_selector_modal_add").modal("show");

            // Initialize PostFinance methods
            this._fetchAndPopulateOnlineMethods();
        },

        // -------------------------------------------------------------------------
        // RENDERING HELPERS
        // -------------------------------------------------------------------------

        /**
         * Renders the list of payment method cards into a specific container
         * Uses the local `this.paymentMethods` state.
         */
        _renderPaymentMethodsList: function ($modal, currentGroupId, containerSelector) {
            var $container = $modal.find(containerSelector);
            $container.empty();

            if (!this.paymentMethods || this.paymentMethods.length === 0) {
                $container.html(QWeb.render("my_compassion.PaymentMethodLoading"));
                return;
            }

            var self = this;
            // Iterate over local state
            _.each(this.paymentMethods, function (method) {
                // Clone data to avoid mutating state
                var data = _.extend({}, method, {
                    // Mark as selected if it matches the current group of the child
                    selected: method.group_id == currentGroupId,
                });

                // Render Client-Side Template
                var $card = $(QWeb.render("my_compassion.PaymentMethodCard", data));
                $container.append($card);
            });
        },

        // -------------------------------------------------------------------------
        // ACTION HANDLERS
        // -------------------------------------------------------------------------

        _onMethodSelectionChange: function (ev) {
            var $input = $(ev.currentTarget);
            var $container = $input.closest(".payment-methods-container, #payment_methods_switch_container");

            // Visual toggle of classes
            $container
                .find(".payment-method-card")
                .removeClass("selected border-core-blue bg-light-blue")
                .addClass("border-gray-200 hover-shadow-sm");

            $input
                .closest(".payment-method-card")
                .addClass("selected border-core-blue bg-light-blue")
                .removeClass("border-gray-200 hover-shadow-sm");
        },

        _onSavePaymentMethod: function (ev) {
            ev.preventDefault();
            var self = this;
            var $btn = $(ev.currentTarget);
            var $modal = $btn.closest(".modal");
            var modalType = $modal.data("modal-type");

            // UI Loading State
            $btn.prop("disabled", true).prepend('<i class="fa fa-spinner fa-spin mr-1"/>');

            var params = {};
            var route = "";

            // --- PREPARE PARAMETERS BASED ON MODAL TYPE ---
            if (modalType == "change") {
                var $selectedInput = $modal.find('input[name="payment_method_selection"]:checked');
                var new_group_id = $selectedInput.attr("group-id");

                route = "/my2/donation/change_method_contract";
                params = {
                    contract_id: $modal.data("contract-id"),
                    group_id: parseInt(new_group_id),
                };
            } else if (modalType == "update") {
                var currentGroupId = $modal.data("group-id");
                route = "/my2/donation/change_method_group";
                params = { group_id: currentGroupId };

                // 1. Check for Group Switch
                var $selectedGroupInput = $modal.find('input[name="payment_method_selection"]:checked');
                if ($selectedGroupInput.length) {
                    var selectedGroupId = $selectedGroupInput.attr("group-id");
                    if (selectedGroupId && parseInt(selectedGroupId) !== parseInt(currentGroupId)) {
                        params.new_group_id = parseInt(selectedGroupId);
                    }
                }

                // 2. Check for Detail Updates
                var $bvrInput = $modal.find('input[name="ref_number"]');
                if ($bvrInput.length) {
                    var newBvrRef = $bvrInput.val();
                    var oldBvrRef = $bvrInput.prop("defaultValue");
                    if (newBvrRef !== oldBvrRef) {
                        params.new_bvr_ref = newBvrRef;
                    }
                }

                if (!params.new_group_id && !params.new_bvr_ref) {
                    this._closeModal($modal, $btn);
                    return;
                }
            } else if (modalType == "add") {
                // Check if Method of provider is selected
                if (this.pfHandler) {
                    this.pfHandler.validate();
                    return;

                } else {
                // Otherwise add a manual (Permanent order or BVR) method
                    route = "/my2/donation/add_payment_method_group";
                    params = {
                        method_type: $modal.find('select[name="method_type"]').val(),
                        recurring_unit: $modal.find('select[name="recurring_unit"]').val(),
                        advance_billing_months: parseInt($modal.find('input[name="advance_billing_months"]').val()),
                    };
                }
            }

            // --- EXECUTE RPC REQUEST ---
            if (route) {
                this._rpc({
                    route: route,
                    params: params,
                })
                    .then(function (result) {
                        if (result.success) {
                            $modal.modal("hide");
                            ToastService.success(_t("The operation was successful."), _t("Success"));

                            // A. UPDATE HTML (Server-Side Rendered List)
                            if (result.html) {
                                var $newContent = $(result.html);
                                // Replace the specific container
                                self.$("#my_sponsorships_container").replaceWith($newContent);
                            }

                            // B. UPDATE STATE (Client-Side Data)
                            if (result.payment_methods) {
                                self.paymentMethods = result.payment_methods;
                            }
                        } else {
                            ToastService.error(result.error || _t("An error occurred."));
                        }
                    })
                    .finally(function () {
                        self._closeModal($modal, $btn);
                    });
            }
        },

        /**
         * Calls backend to create transaction and get available PostFinance methods.
         */
        _fetchAndPopulateOnlineMethods: function () {
            var self = this;
            var $select = this.$('#new_method_type');

            if ($select.data('loaded')) return; // Avoid duplicate calls

            var unit = this.$('select[name="recurring_unit"]').val() || 'month';
            var val = this.$('input[name="advance_billing_months"]').val() || 1;

            ajax.jsonRpc('/my2/donation/add_payment_method_online', 'call', {
                'recurring_unit': unit,
                'recurring_value': val
            }).then(function (result) {
                if (result.success && result.iframe_url && result.pf_methods) {

                    // Load the JS library
                    $.getScript(result.iframe_url, function () {
                        console.log("PostFinance JS Loaded");
                    });

                    // Append options directly to the main select
                    result.pf_methods.forEach(function (method) {
                        $select.append($('<option>', {
                            value: 'pf_' + method.id,
                            text: method.name
                        }));
                    });

                    $select.data('loaded', true);
                }
            });
        },

        // --- 2. Handle Selection Change ---
        _onAddMethodChange: function (ev) {
            var $target = $(ev.currentTarget);
            var value = $target.val();
            var $configFields = this.$('#payment_config_fields');
            var $iframeContainer = this.$('#postfinance-iframe-container');
            var $loading = this.$('#pf-iframe-loading');
            var $paymentForm = this.$('#payment-form');

            // Reset
            $paymentForm.empty();
            this.pfHandler = null;

            if (value && value.startsWith('pf_')) {
                // === ONLINE MODE ===
                // 1. Get the readable name (e.g., "Twint", "Visa")
                var methodName = $target.find('option:selected').text();
                
                // 2. Send to Backend immediately
                ajax.jsonRpc('/my2/donation/set_selected_payment_method', 'call', {
                    method_name: methodName
                });

                // 1. Hide Config Fields
                $configFields.hide();

                // 2. Show Iframe Container
                $iframeContainer.show();
                $loading.show();
                $paymentForm.hide();

                // 3. Initialize Iframe
                var configurationId = String(value.split('_')[1]);

                if (window.IframeCheckoutHandler) {
                    try {
                        var handler = window.IframeCheckoutHandler(configurationId);

                        handler.setValidationCallback(function (validationResult) {
                            if (validationResult.success) {
                                handler.submit();
                            } else {
                                var btn = $('#btn_save_payment_method');
                                btn.attr('disabled', false).find('i').remove();
                                alert("Please check your input.");
                            }
                        });

                        handler.setInitializeCallback(function () {
                            $loading.hide();
                            $paymentForm.show();
                        });

                        // Handler for height adjustment if needed
                        handler.setHeightChangeCallback(function (height) {
                            $paymentForm.height(height);
                        });

                        handler.create('payment-form');
                        this.pfHandler = handler; // Save for submit button

                    } catch (e) {
                        console.error(e);
                        $loading.text("Error loading payment interface.");
                    }
                } else {
                    $loading.text("Payment library still loading...");
                }

            } else {
                // === MANUAL MODE ===
                $configFields.show();
                $iframeContainer.hide();
            }
        },

        /**
         * Custom Submit Button logic for Iframe
         */
        _onSubmitPostFinance: function (ev) {
            ev.preventDefault();
            if (this.pfHandler) {
                var $btn = $(ev.currentTarget);
                $btn.attr('disabled', true).prepend('<i class="fa fa-spinner fa-spin mr-1"></i>');
                // Triggers the validation callback defined above
                this.pfHandler.validate();
            }
        },

        _closeModal: function ($modal, $btn) {
            $modal.modal("hide");
            $btn.prop("disabled", false).find(".fa-spinner").remove();
        },

        _onModalHidden: function ($modal) {
            // Cleanup data attached to DOM
            $modal.removeData(["group-id", "contract-id"]);
            $modal.find('input[type="radio"]').prop("checked", false);
            // Also reset form inputs if needed
            $modal.find('input[type="text"]').val(function () {
                return this.defaultValue;
            });
        },

        _onModalHiddenGlobal: function (ev) {
            var $modal = $(ev.target);
            if ($modal.attr("id") && $modal.attr("id").startsWith("payment_method_selector_modal")) {
                this._onModalHidden($modal);
            }
        },

        // -------------------------------------------------------------------------
        // TOASTS & HISTORY
        // -------------------------------------------------------------------------

        /**
         * Checks URL parameters on page load to display Toasts.
         * The parameters are injected by the PostFinance Feedback Controller.
         */
        _checkAddPaymentMethod: function () {
            var urlParams = new URLSearchParams(window.location.search);
            
            var res = urlParams.get("payment_method_result"); // e.g. "Success", "Error", "Already Saved"
            var msg = urlParams.get("payment_method_message"); // The text from create_from_transaction

            if (res && msg) {
                // Decode URI component to handle spaces and special chars correctly
                msg = decodeURIComponent(msg);

                if (res === "Success") {
                    ToastService.success(msg, _t("Success"));
                } 
                else if (res === "Error") {
                    ToastService.error(msg, _t("Error"));
                } 
                else if (res === "Already Saved") {
                    // Specific toast for duplicates (info instead of success/error)
                    ToastService.info(msg, _t("Info"));
                }
                else {
                    // Fallback
                    ToastService.info(msg, _t("Info"));
                }

                // Clean URL so the toast doesn't appear again on refresh
                this._cleanUrlParams(['payment_method_result', 'payment_method_message']);
            }
        },

        /**
         * Helper to remove params from URL without reloading
         */
        _cleanUrlParams: function(keysToRemove) {
            var urlParams = new URLSearchParams(window.location.search);
            var changed = false;
            
            keysToRemove.forEach(function(key) {
                if (urlParams.has(key)) {
                    urlParams.delete(key);
                    changed = true;
                }
            });

            if (changed) {
                var newUrl = window.location.pathname + (urlParams.toString() ? "?" + urlParams.toString() : "");
                window.history.replaceState({}, document.title, newUrl);
            }
        },

        _onPagerClick: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            if ($btn.hasClass("disabled")) return;
            var page = $btn.data("page");
            if (page) this._updateHistory(page);
        },

        _updateHistory: function (page) {
            var self = this;
            var $container = this.$("#donation_history_container");
            var $buttons = this.$("#history_pager_prev, #history_pager_next");
            $buttons.addClass("disabled");

            this._rpc({
                route: "/my2/donations/history",
                params: { invoice_page: page },
            })
                .then(function (result) {
                    if (result.html && $container.length) {
                        $container.replaceWith(result.html);
                    }
                })
                .finally(function () {
                    self.$("#history_pager_prev, #history_pager_next").removeClass("disabled");
                });
        },
    });
});
