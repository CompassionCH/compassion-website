document.addEventListener("DOMContentLoaded", function () {
    odoo.define('my_compassion.my2_donations', function (require) {
        'use strict';

        var publicWidget = require('web.public.widget');
        var core = require('web.core');
        var QWeb = core.qweb;
        var _t = core._t;
        var rpc = require('web.rpc');

        publicWidget.registry.My2Donations = publicWidget.Widget.extend({
            selector: '.my2-donations-page',

            xmlDependencies: ['/my_compassion/templates/components/my2_payment_method_modal.xml'],

            events: {
                // Listen for the custom event triggered by the "Change" button
                'open_payment_method_selector': '_onOpenPaymentSelector',

                // Modal actions
                'click #btn_save_payment_method': '_onSavePaymentMethod',
                'change input[name="payment_method_selection"]': '_onMethodSelectionChange',

                // Pager actions
                'click #history_pager_prev, #history_pager_next': '_onPagerClick',
            },

            /**
             * Standard Odoo start method.
             */
            start: function () {
                console.log("My2Donations widget started.");
                var self = this;
                // Bind the hidden event manually because the modal might be moved in DOM
                $('#payment_method_selector_modal').on('hidden.bs.modal', function () {
                    self._onModalHidden($(this));
                });
                return this._super.apply(this, arguments);
            },

            destroy: function () {
                $('#payment_method_selector_modal').off('hidden.bs.modal');
                this._super.apply(this, arguments);
            },

            // -------------------------------------------------------------------------
            // EVENT HANDLERS
            // -------------------------------------------------------------------------

            /**
             * Opens the modal and sets up the text/data based on the event detail.
             */
            _onOpenPaymentSelector: function (ev) {
                // Handle both jQuery event wrapper and native event
                var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
                if (!detail) return;

                var $modal = $('#payment_method_selector_modal');
                if (!$modal.length) return;

                // Dynamic Texts
                var modalType = detail.modal_type;
                var title = modalType + ' Payment Method';
                $modal.find('#payment_method_modal_title').text(title);

                var descriptions = {
                    'Update': 'Update your payment method details below.',
                    'Add': 'Add a new payment method to your account.',
                    'Change': 'Change your payment method for ' + (detail.child_name || 'this sponsorship') + '.',
                };
                var description = detail.description || descriptions[modalType] || descriptions['Update'];
                $modal.find('#payment_method_modal_desc').text(description);

                // Store Context Data
                //$modal.data('group-id', detail.group_id);
                $modal.data('modal-type', modalType);

                // Update hidden input if you use form submission (optional with RPC)
                $('#selected_contract_group_id').val(detail.group_id);

                // Load Methods (If switching specific contract)
                // Only load if we are in "Change" mode or "Add" mode logic
                if (modalType === 'Change') {
                    $modal.data('contract-id', detail.contract_id);
                    $modal.data('group-id', detail.group_id);
                    this._loadPaymentMethods($modal);
                }

                $modal.modal('show');
            },

            /**
             * Fetches available methods from server and renders them using QWeb.
             */
            _loadPaymentMethods: function ($modal, group_id) {
                var $container = $modal.find('#payment_methods_list_container');


                // Render Loading Spinner
                $container.html(QWeb.render('my_compassion.my2_payment_method_loading'));

                this._rpc({
                    route: '/my2/payment/get_payment_methods_sponsor',

                }).then(function (methods) {
                    $container.empty();

                    if (!methods || methods.length === 0) {
                        $container.html('<div class="text-center text-muted p-3">No payment methods found.</div>');
                        return;
                    }

                    // Render Cards
                    _.each(methods, function (method) {
                        // Determine if selected (logic can be enhanced)
                        method.selected = false;
                        var $card = $(QWeb.render('my_compassion.my2_payment_method_display_card', method));
                        $container.append($card);
                    });
                }).catch(function (err) {
                    $container.html('<div class="text-danger text-center">Error loading payment methods.</div>');
                    console.error("RPC Error:", err);
                });
            },

            /**
             * Visual feedback when selecting a radio button card
             */
            _onMethodSelectionChange: function (ev) {
                var $input = $(ev.currentTarget);
                var $container = this.$('#payment_methods_list_container');

                // Remove 'selected' style from all
                $container.find('.payment-method-card')
                    .removeClass('selected border-core-blue bg-light-blue-10')
                    .addClass('border-gray-200 hover-shadow-sm');

                // Add 'selected' style to active
                $input.closest('.payment-method-card')
                    .addClass('selected border-core-blue bg-light-blue-10')
                    .removeClass('border-gray-200 hover-shadow-sm');
            },

            /**
             * Save button handler
             */
            _onSavePaymentMethod: function (ev) {
                ev.preventDefault();
                var $modal = $('#payment_method_selector_modal');
                var selection = $modal.find('input[name="payment_method_selection"]:checked').val();

                if (!selection) {
                    alert(_t("Please select a payment method."));
                    return;
                }

                var parts = selection.split('-'); // e.g. "token-10"
                var type = parts[0];
                var id = parseInt(parts[1]);

                var $btn = $(ev.currentTarget);
                $btn.prop('disabled', true).prepend('<i class="fa fa-spinner fa-spin mr-1"/>');

                this._rpc({
                    route: '/my2/payment/update_method',
                    params: {
                        contract_id: $modal.data('contract-id'),
                        group_id: $modal.data('group-id'),
                        method_type: type,
                        method_id: id
                    }
                }).then(function (result) {
                    if (result.success) {
                        $modal.modal('hide');
                        window.location.reload();
                    } else {
                        alert(_t("Error: ") + (result.error || "Unknown"));
                    }
                }).finally(function () {
                    $btn.prop('disabled', false).find('.fa-spinner').remove();
                });
            },

            _onModalHidden: function ($modal) {
                $modal.removeData(['group-id', 'contract-id', 'modal-type']);
                $modal.find('#modal_title').text('Payment Method');
                $modal.find('#modal_description').text('Select a payment method.');
                $modal.find('#payment_methods_list_container').empty();
            },

            // -------------------------------------------------------------------------
            // PAGER LOGIC
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

                rpc.query({
                    route: "/my2/donations/history",
                    params: { invoice_page: page },
                }).then(function (result) {
                    if (result.html) {
                        // Use replaceWith to swap the content
                        if ($container.length) {
                            $container.replaceWith(result.html);
                        }
                    }
                }).finally(function () {
                    // Re-query buttons because DOM changed
                    self.$('#history_pager_prev, #history_pager_next').removeClass('disabled');
                });
            }
        });
        return publicWidget.registry.My2Donations;
    });
});