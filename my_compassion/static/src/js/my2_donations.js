odoo.define('my_compassion.my2_donations', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    const ToastService = require("my_compassion.toast_service");
    var _t = core._t;

    publicWidget.registry.My2Donations = publicWidget.Widget.extend({
        // This class MUST appear on a div in your page for the widget to start
        selector: '.my2-donations-page',

        // Load the QWeb templates for the client-side rendering
        xmlDependencies: ['/my_compassion/static/src/xml/my2_payment_method_templates.xml'],


        events: {
            'open_payment_method_selector': '_onOpenPaymentSelector',

            'open_payment_method_update': '_onOpenPaymentMethodUpdate',
            'open_payment_method_change': '_onOpenPaymentMethodChange',
            'open_payment_method_add': '_onOpenPaymentMethodAdd',

            'click #btn_save_payment_method': '_onSavePaymentMethod',
            'change input[name="payment_method_selection"]': '_onMethodSelectionChange',
            'click #history_pager_prev, #history_pager_next': '_onPagerClick',
        },

        /**
         * Widget Initialization
         */
        start: function () {
            console.log("My2Donations Public Widget started.");
            var self = this;

            // 1. Global Listener for Modal Hidden (Cleanup)
            $('body').on('hidden.bs.modal', '.modal', function () {
                // Check if it's one of our payment modals
                if ($(this).attr('id') && $(this).attr('id').startsWith('payment_method_selector_modal')) {
                    self._onModalHidden($(this));
                }
            });

            // 2. Global Listener for Payment Selection Change
            // Allows handling events even if Bootstrap moves the modal outside our widget's scope
            $('body').on('change', 'input[name="payment_method_selection"]', this._onMethodSelectionChange.bind(this));

            return this._super.apply(this, arguments);
        },

        destroy: function () {
            $('body').off('hidden.bs.modal', '#payment_method_selector_modal_update');
            this._super.apply(this, arguments);
        },

        // -------------------------------------------------------------------------
        // HANDLERS
        // -------------------------------------------------------------------------

        _onOpenPaymentMethodUpdate: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            var groupId = detail ? detail.group_id : null;
            var methodInfo = detail ? detail.method_info : null;

            var $modalUpdate = $('#payment_method_selector_modal_update');
            var $container = $modalUpdate.find('#modal_container').empty();
            $container.html(QWeb.render('my_compassion.PaymentMethodUpdateAccordion', methodInfo));

            this._renderPaymentMethods($modalUpdate, groupId, '#payment_methods_switch_container');
            $modalUpdate.modal('show');
        },

        _onOpenPaymentMethodChange: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            var groupId = detail ? detail.group_id : null;
            var contractId = detail ? detail.contract_id : null;
            var childName = detail ? detail.child_name : null;

            console.log("Opening Payment Method Change Modal for Group ID:", groupId, "Contract ID:", contractId, "Child Name:", childName);
            var $modalChange = $('#payment_method_selector_modal_change');
            $modalChange.find('#modal_description').empty().text('Change your payment method for ' + (childName || 'your sponsored child') + '.');
            $modalChange.data('contract-id', contractId);

            this._renderPaymentMethods($modalChange, groupId, '#modal_container');

            $modalChange.modal('show');
        },

        // Helper to render payment methods into a modal
        _renderPaymentMethods: function ($modal, groupId, cardContainer) {
            var paymentMethods = $modal.data('payment-methods');
            var $modalContainer = $modal.find(cardContainer);
            $modalContainer.empty();

            _.each(paymentMethods, function (method) {
                if (method.group_id == groupId) {
                    method.selected = true;
                }
                var $card = $(QWeb.render('my_compassion.PaymentMethodCard', method));
                $modalContainer.append($card);
            });
        },

        // Render selected card highlighted
        _onMethodSelectionChange: function (ev) {
            var $input = $(ev.currentTarget);
            var $container = $input.closest('#modal_container');

            $container.find('.payment-method-card')
                .removeClass('selected border-core-blue bg-light-blue')
                .addClass('border-gray-200 hover-shadow-sm');

            $input.closest('.payment-method-card')
                .addClass('selected border-core-blue bg-light-blue')
                .removeClass('border-gray-200 hover-shadow-sm');
        },

        _onSavePaymentMethod: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            var $modal = $btn.closest('.modal');
            var modalType = $modal.data('modal-type');

            console.log("Saving Payment Method. Type:", modalType);
            $btn.prop('disabled', true).prepend('<i class="fa fa-spinner fa-spin mr-1"/>');

            if (modalType == 'change') {
                var $selectedInput = $modal.find('input[name="payment_method_selection"]:checked');
                var new_group_id = $selectedInput.attr('group-id');
                console.log("Inside the if: new_group_id", new_group_id);

                this._rpc({
                    route: '/my2/donation/change_method_contract',
                    params: {
                        contract_id: $modal.data('contract-id'),
                        group_id: new_group_id,
                    }
                }).then(function (result) {
                    if (result.success) {
                        $modal.modal('hide');

                        ToastService.success(_t("Payment method changed successfully."), _t("Success"));

                        // Optional: longer delay if you want them to read it fully
                        setTimeout(() => window.location.reload(), 2000);

                    } else {
                        ToastService.error(result.error || _t("An error occurred while changing the payment method."));
                    }
                }).finally(function () {
                    $btn.prop('disabled', false).find('.fa-spinner').remove();
                });

            } else if (modalType == 'update') {
                if ($modal.find('#collapseList').hasClass('show')) {
                    // USER IS SWITCHING METHOD
                    var $selectedInput = $modal.find('input[name="payment_method_selection"]:checked');
                    var new_group_id = $selectedInput.attr('group-id');
                    console.log("Switching to Payment Method Group ID:", new_group_id);
                    this._rpc({
                        route: '/my2/donation/change_method_group',
                        params: {
                            group_id: $modal.data('group-id'),
                            new_group_id: new_group_id,
                        }
                    }).then(function (result) {
                        if (result.success) {
                            $modal.modal('hide');
                            window.location.reload();
                            console.log("Payment method switched successfully.");
                            ToastService.success(_t("Payment method switched successfully."));
                        } else {
                            ToastService.error(result.error || _t("An error occurred while switching the payment method."));
                        }
                    }).finally(function () {
                        $btn.prop('disabled', false).find('.fa-spinner').remove();
                        ToastService.info("TEST")
                    });
                } else {
                    // USER IS UPDATING DETAILS (Form)
                    // TODO: Implement update form submission logic here
                    var formData = {};
                    $modal.find('#payment_method_form input').each(function () {
                        if (this.name) formData[this.name] = $(this).val();
                    });
                    console.log("Updating Payment Details:", formData);
                    alert("Update logic not implemented in this demo.");
                }
            }
        },

        _onModalHidden: function ($modal) {
            $modal.removeData(['group-id']);
            $modal.find('input[type="radio"]').prop('checked', false);
        },

        // -------------------------------------------------------------------------
        // Pagination for Donation History
        // -------------------------------------------------------------------------
        _onPagerClick: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            if ($btn.hasClass('disabled')) return;

            var page = $btn.data('page');
            if (page) {
                this._updateHistory(page);
            }
        },

        _updateHistory: function (page) {
            var self = this;
            var $container = this.$('#donation_history_container');
            var $buttons = this.$('#history_pager_prev, #history_pager_next');

            $buttons.addClass('disabled');

            this._rpc({
                route: "/my2/donations/history",
                params: { invoice_page: page },
            }).then(function (result) {
                if (result.html) {
                    if ($container.length) {
                        $container.replaceWith(result.html);
                    }
                }
            }).finally(function () {
                self.$('#history_pager_prev, #history_pager_next').removeClass('disabled');
            });
        }
    });
}); 