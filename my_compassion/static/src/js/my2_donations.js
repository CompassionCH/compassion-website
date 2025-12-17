odoo.define("my_compassion.my2_donations", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");
    var core = require("web.core");
    var QWeb = core.qweb;
    const ToastService = require("my_compassion.toast_service");
    var _t = core._t;

    publicWidget.registry.My2Donations = publicWidget.Widget.extend({
        // This class MUST appear on a div in your page for the widget to start
        selector: ".my2-donations-page",

        // Load the QWeb templates for the client-side rendering
        xmlDependencies: ["/my_compassion/static/src/xml/my2_payment_method_templates.xml"],

        events: {
            open_payment_method_selector: "_onOpenPaymentSelector",

            open_payment_method_update: "_onOpenPaymentMethodUpdate",
            open_payment_method_change: "_onOpenPaymentMethodChange",
            open_payment_method_add: "_onOpenPaymentMethodAdd",

            "click #btn_save_payment_method": "_onSavePaymentMethod",
            'change input[name="payment_method_selection"]': "_onMethodSelectionChange",
            "click #history_pager_prev, #history_pager_next": "_onPagerClick",
        },

        /**
         * Widget Initialization
         */
        start: function () {
            var self = this;

            // Store bound handlers to allow proper unbinding in destroy()
            // This prevents memory leaks and zombie listeners
            this._onModalHiddenGlobalBound = this._onModalHiddenGlobal.bind(this);
            this._onMethodSelectionChangeBound = this._onMethodSelectionChange.bind(this);

            // 1. Global Listener for Modal Hidden (Cleanup)
            // We bind to 'body' because Bootstrap sometimes moves modals to the end of the DOM
            $("body").on("hidden.bs.modal", ".modal", this._onModalHiddenGlobalBound);

            // 2. Global Listener for Payment Selection Change
            $("body").on("change", 'input[name="payment_method_selection"]', this._onMethodSelectionChangeBound);

            // 3. If a payment method was just added display a success toast
            this._checkAddPaymentMethod();

            return this._super.apply(this, arguments);
        },

        /**
         * Clean up global event listeners
         */
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
        // HANDLERS
        // -------------------------------------------------------------------------

        _onModalHiddenGlobal: function (ev) {
            var $modal = $(ev.target);
            // Check if it's one of our payment modals
            if ($modal.attr("id") && $modal.attr("id").startsWith("payment_method_selector_modal")) {
                this._onModalHidden($modal);
            }
        },

        _checkAddPaymentMethod: function () {
            var urlParams = new URLSearchParams(window.location.search);
            var paymentMethodResult = urlParams.get("payment_method_result");
            var paymentMethodMessage = urlParams.get("payment_method_message");

            if (paymentMethodResult === "Success") {
                ToastService.success(_t(paymentMethodMessage), _t(paymentMethodResult));
            } else if (paymentMethodResult === "Error") {
                ToastService.error(_t(paymentMethodMessage), _t(paymentMethodResult));
            } else if (paymentMethodResult === "Already Saved") {
                ToastService.info(_t(paymentMethodMessage), _t(paymentMethodResult));
            }

            // Clean the URL – remove the two parameters we just processed
            urlParams.delete("payment_method_result");
            urlParams.delete("payment_method_message");

            var cleanSearch = urlParams.toString();
            var newUrl = window.location.pathname + (cleanSearch ? "?" + cleanSearch : "");

            window.history.replaceState({}, document.title, newUrl);
        },

        _onOpenPaymentMethodUpdate: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            var groupId = detail ? detail.group_id : null;
            var methodInfo = detail ? detail.method_info : null;

            var $modalUpdate = $("#payment_method_selector_modal_update");
            // Store the group-id on the modal so _onSavePaymentMethod can find it
            $modalUpdate.data("group-id", groupId);
            var $container = $modalUpdate.find("#modal_container").empty();
            $container.html(QWeb.render("my_compassion.PaymentMethodUpdateAccordion", methodInfo));

            this._renderPaymentMethods($modalUpdate, groupId, "#payment_methods_switch_container");
            $modalUpdate.modal("show");
        },

        _onOpenPaymentMethodChange: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            var groupId = detail ? detail.group_id : null;
            var contractId = detail ? detail.contract_id : null;
            var childName = detail ? detail.child_name : null;

            var $modalChange = $("#payment_method_selector_modal_change");
            $modalChange
                .find("#modal_description")
                .empty()
                .text(_.str.sprintf(_t("Change your payment method for %s."), childName || _t("your sponsored child")));
            $modalChange.data("contract-id", contractId);

            this._renderPaymentMethods($modalChange, groupId, "#modal_container");

            $modalChange.modal("show");
        },

        _onOpenPaymentMethodAdd: function (ev) {
            var $modalAdd = $("#payment_method_selector_modal_add");
            var $container = $modalAdd.find("#add_payment_method_container");

            $modalAdd.modal("show");
        },

        // Helper to render payment methods into a modal
        _renderPaymentMethods: function ($modal, groupId, cardContainer) {
            var paymentMethods = $modal.data("payment-methods");
            var $modalContainer = $modal.find(cardContainer);
            $modalContainer.empty();

            _.each(paymentMethods, function (method) {
                if (method.group_id == groupId) {
                    method.selected = true;
                }
                var $card = $(QWeb.render("my_compassion.PaymentMethodCard", method));
                $modalContainer.append($card);
            });
        },

        // Render selected card highlighted
        _onMethodSelectionChange: function (ev) {
            var $input = $(ev.currentTarget);
            var $container = $input.closest(".payment-methods-container, #payment_methods_switch_container");

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
            var $btn = $(ev.currentTarget);
            var $modal = $btn.closest(".modal");
            var modalType = $modal.data("modal-type");

            $btn.prop("disabled", true).prepend('<i class="fa fa-spinner fa-spin mr-1"/>');

            var promise;

            // CASE 1: CHANGE (Contract Level)
            if (modalType == "change") {
                var $selectedInput = $modal.find('input[name="payment_method_selection"]:checked');
                var new_group_id = $selectedInput.attr("group-id");

                promise = this._rpc({
                    route: "/my2/donation/change_method_contract",
                    params: {
                        contract_id: $modal.data("contract-id"),
                        group_id: parseInt(new_group_id),
                    },
                });

                // CASE 2: UPDATE (Group Level) - Merge or Edit Details
            } else if (modalType == "update") {
                var currentGroupId = $modal.data("group-id");

                var params = {
                    group_id: currentGroupId,
                };

                // Check for Group Switch (Merge)
                // We check if a radio button is selected AND if its group-id differs from current
                var $selectedGroupInput = $modal.find('input[name="payment_method_selection"]:checked');
                if ($selectedGroupInput.length) {
                    var selectedGroupId = $selectedGroupInput.attr("group-id");
                    if (selectedGroupId && parseInt(selectedGroupId) !== parseInt(currentGroupId)) {
                        params.new_group_id = parseInt(selectedGroupId);
                    }
                }

                // Check for Detail Updates (BVR or LSV Reference)
                // We compare the current input value with its default value (original value)
                var $bvrInput = $modal.find('input[name="ref_number"]');
                if ($bvrInput.length) {
                    var newBvrRef = $bvrInput.val();
                    var oldBvrRef = $bvrInput.prop("defaultValue");

                    // Only add to params if it actually changed
                    if (newBvrRef !== oldBvrRef) {
                        params.new_bvr_ref = newBvrRef;
                    }
                }

                // If nothing relevant changed, just close the modal
                if (!params.new_group_id && !params.new_bvr_ref) {
                    $modal.modal("hide");
                    $btn.prop("disabled", false).find(".fa-spinner").remove();
                    return;
                }

                promise = this._rpc({
                    route: "/my2/donation/change_method_group",
                    params: params,
                });

                // CASE 3: ADD (New Manual Method)
            }
            if (modalType == "add") {
                // Retrieve Form Data
                var methodType = $modal.find('select[name="method_type"]').val();
                var recurringUnit = $modal.find('select[name="recurring_unit"]').val();
                var advanceMonths = $modal.find('input[name="advance_billing_months"]').val();

                promise = this._rpc({
                    route: "/my2/donation/add_payment_method_group",
                    params: {
                        method_type: methodType,
                        recurring_unit: recurringUnit,
                        advance_billing_months: parseInt(advanceMonths),
                    },
                });
            }

            // Execute Request
            if (promise) {
                promise
                    .then(function (result) {
                        if (result.success) {
                            $modal.modal("hide");
                            ToastService.success(_t("The operation was successfull."), _t("Success"));
                            setTimeout(() => window.location.reload(), 1000);
                        } else {
                            ToastService.error(result.error || _t("An error occurred."));
                        }
                    })
                    .finally(function () {
                        $btn.prop("disabled", false).find(".fa-spinner").remove();
                    });
            } else {
                // Fallback if promise wasn't created (should be covered by early return above)
                $modal.modal("hide");
                $btn.prop("disabled", false).find(".fa-spinner").remove();
            }
        },

        _onModalHidden: function ($modal) {
            $modal.removeData(["group-id"]);
            $modal.find('input[type="radio"]').prop("checked", false);
        },

        // -------------------------------------------------------------------------
        // Pagination for Donation History
        // -------------------------------------------------------------------------
        _onPagerClick: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            if ($btn.hasClass("disabled")) return;

            var page = $btn.data("page");
            if (page) {
                this._updateHistory(page);
            }
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
                    if (result.html) {
                        if ($container.length) {
                            $container.replaceWith(result.html);
                        }
                    }
                })
                .finally(function () {
                    self.$("#history_pager_prev, #history_pager_next").removeClass("disabled");
                });
        },
    });
});
