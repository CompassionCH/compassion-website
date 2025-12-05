odoo.define('my_compassion.my2_donations', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    publicWidget.registry.My2Donations = publicWidget.Widget.extend({
        // This class MUST appear on a div in your page for the widget to start
        selector: '.my2-donations-page',

        // Load the QWeb templates for the client-side rendering
        xmlDependencies: ['/my_compassion/static/src/xml/my2_payment_method_templates.xml'],


        events: {
            'open_payment_method_selector': '_onOpenPaymentSelector',

            // New dedicated handlers
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

            // Bind Bootstrap modal hidden event
            // We bind to 'body' because Bootstrap sometimes moves modals to the end of the DOM
            $('body').on('hidden.bs.modal', '#payment_method_selector_modal_update', function () {
                self._onModalHidden($(this));
            });

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
            // var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            // var groupId = detail ? detail.group_id : null;
            // var methodInfo = detail ? detail.method_info : null;
            // console.log("Opening Payment Method Update Modal for Group ID:", methodInfo);
            var $modalUpdate = $('#payment_method_selector_modal_update');
            $modalUpdate.modal('show');
        },

        _onOpenPaymentMethodChange: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            var groupId = detail ? detail.group_id : null;
            var contractId = detail ? detail.contract_id : null;
            var childName = detail ? detail.child_name : null;
            console.log("Opening Payment Method Change Modal for Group ID:", groupId, "Contract ID:", contractId, "Child Name:", childName);
            var $modalChange = $('#payment_method_selector_modal_change');
            $modal.find('#modal_description').empty().text('Change your payment method for ' + (childName || 'your sponsored child') + '.');
            

            $modalChange.modal('show');
        },

         _onOpenPaymentSelector: function (ev) {
            var detail = ev.originalEvent ? ev.originalEvent.detail : ev.detail;
            if (!detail) return;
            console.log("Opening payment selector with detail:", detail);

            var $modalUpdate = $('#payment_method_selector_modal_update');
            var $modalAdd = $('#payment_method_selector_modal_add');

            var button = $(ev.relatedTarget); // Button that triggered the modal
            var groupId = button.data('group-id');

            console.log("Modal Add:", $modalAdd);
            console.log("Modal Update:", $modalUpdate);
            console.log("Group ID from button:", groupId);


                // if (!$modal.length) {
                //     console.error("Modal #payment_method_selector_modal not found.");
                //     return;
                // }

                // // 1. Update Texts
                // var modalType = detail.modal_type || 'Update';
                // var title = modalType + ' Payment Method';
                // $modal.find('#modal_title').text(title);

                // // Define Descriptions based on Type
                // var descriptions = {
                //     'Update': 'Update your payment method.',
                //     'Add': 'Add a new payment method to your account.',
                //     'Change': 'Change your payment method for ' + (detail.child_name || 'your sponsored child') + '.',
                // };
                // // Set description
                // $modal.find('#modal_description').text(descriptions[detail.modal_type]);

                // // Store Context
                // $modal.data('modal-type', modalType);
                // $modal.data('group-id', detail.group_id);

                // // Update hidden input
                // $('#selected_contract_group_id').val(detail.group_id);

                // // Load Methods Logic
                // // Clear previous list
                // $modal.find('#modal_container').empty();

                // if (modalType == 'Change') {
                //     $modal.data('contract-id', detail.contract_id);
                //     this._loadPaymentMethods($modal);
                // }

                // if (modalType == 'Update') {
                //     var $container = $modal.find('#modal_container');

                //     /*
                //     var group_info = detail.group_info || {};
                //     var formHtml = QWeb.render('my_compassion.PaymentMethodUpdateForm', group_info);
                //     console.log("Rendering Update Form with data:", formHtml);
                //     $container.html(formHtml);

                //     var $listWrapper = $('<div/>');
                //     $container.append($listWrapper);
                //     this._loadPaymentMethods($modal, $listWrapper);
                //     */
                //     // --- UPDATE MODE: ACCORDION (Form + Switch List) ---

                //     // Create Wrapper
                //     var $accordion = $('<div/>', { id: 'payment_method_accordion', class: 'accordion' });

                //     // A. Update Form Section
                //     var info = detail.method_info || detail.group_info || {};
                //     info.is_card = (info.type === 'token' || info.is_card);

                //     var $headerForm = this._createAccordionSectionHeader('collapseForm', _t('Update Current Details'), true);
                //     var $bodyForm = $('<div/>', { id: 'collapseForm', class: 'collapse show', 'data-parent': '#payment_method_accordion' });
                //     var $contentForm = $('<div/>', { class: 'pt-3 pl-1 pr-1' });

                //     $contentForm.html(QWeb.render('my_compassion.PaymentMethodUpdateForm', info));
                //     $bodyForm.append($contentForm);

                //     $accordion.append($('<div/>', { class: 'border-bottom mb-2' }).append($headerForm).append($bodyForm));

                //     // B. Switch List Section
                //     var $headerList = this._createAccordionSectionHeader('collapseList', _t('Switch Payment Method'), false);
                //     var $bodyList = $('<div/>', { id: 'collapseList', class: 'collapse', 'data-parent': '#payment_method_accordion' });
                //     var $contentList = $('<div/>', { class: 'pt-3' });

                //     this._loadPaymentMethods($modal, $contentList); // Load into specific container
                //     $bodyList.append($contentList);

                //     $accordion.append($('<div/>', { class: 'border-bottom' }).append($headerList).append($bodyList));

                //     $container.append($accordion);

                //     // Bind visual events (arrows, button text)
                //     this._bindAccordionEvents($modal);

                //     // Initial Button Text
                //     $modal.find('#btn_save_payment_method').text(_t('Update Details'));


               // }

            // $modal.modal('show');
        },

        _loadPaymentMethods: function ($modal, $targetContainer) {
            var $container = $targetContainer || $modal.find('#modal_container');
            console.log("Loading payment methods into container:", $container);

            // Render Loading Spinner
            // Ensure 'my_compassion.PaymentMethodLoading' exists in your XML file
            $container.html(QWeb.render('my_compassion.PaymentMethodLoading'));

            this._rpc({
                route: '/my2/donations/get_payment_methods_sponsor',
                params: {}
            }).then(function (methods) {
                $container.empty();

                if (!methods || methods.length === 0) {
                    $container.html('<div class="text-center text-muted p-3">' + _t('No payment methods found.') + '</div>');
                    return;
                }

                // Render Cards
                _.each(methods, function (method) {
                    console.log("Rendering payment method:", method);
                    if (method.group_id == $modal.data('group-id')) {
                        method.selected = true;
                    }
                    var $card = $(QWeb.render('my_compassion.PaymentMethodCard', method));
                    $container.append($card);
                });
            }).catch(function (err) {
                $container.html('<div class="text-danger text-center">' + _t('Error loading payment methods.') + '</div>');
                console.error("RPC Error:", err);
            });
        },


        // Render selected card highlighted
        _onMethodSelectionChange: function (ev) {
            var $input = $(ev.currentTarget);
            var $container = this.$('#modal_container');

            $container.find('.payment-method-card')
                .removeClass('selected border-core-blue bg-light-blue')
                .addClass('border-gray-200 hover-shadow-sm');

            $input.closest('.payment-method-card')
                .addClass('selected border-core-blue bg-light-blue')
                .removeClass('border-gray-200 hover-shadow-sm');
        },

        _onSavePaymentMethod: function (ev) {
            ev.preventDefault();


            var $modal = $('#payment_method_selector_modal');
            var modal_type = $modal.data('modal-type');

            var $btn = $(ev.currentTarget);
            $btn.prop('disabled', true).prepend('<i class="fa fa-spinner fa-spin mr-1"/>');

            if (modal_type == 'Change') {
                var $selectedInput = $modal.find('input[name="payment_method_selection"]:checked');
                var new_group_id = $selectedInput.attr('group-id');

                this._rpc({
                    route: '/my2/donation/change_method_contract',
                    params: {
                        contract_id: $modal.data('contract-id'),
                        group_id: new_group_id,
                    }
                }).then(function (result) {
                    if (result.success) {
                        $modal.modal('hide');
                        window.location.reload();
                        console.log("Payment method changed successfully.");
                        ToastService.success(_t("Payment method changed successfully."));
                    } else {
                        ToastService.error(result.error || _t("An error occurred while changing the payment method."));
                    }
                }).finally(function () {
                    $btn.prop('disabled', false).find('.fa-spinner').remove();
                });

            } else if (modal_type == 'Update') {
                if ($modal.find('#collapseList').hasClass('show')) {
                    // USER IS SWITCHING METHOD
                    // this._saveSwitchMethod($modal, $btn, modalType);
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
            $modal.removeData(['group-id', 'contract-id', 'modal-type']);
            $modal.find('#payment_method_modal_title').text(_t('Payment Method'));
            $modal.find('#payment_method_modal_desc').text(_t('Select a payment method.'));
            $modal.find('#modal_container').empty();
            $modal.find('input[type="radio"]').prop('checked', false);
        },

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