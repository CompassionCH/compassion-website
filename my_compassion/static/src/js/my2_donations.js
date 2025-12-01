document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.donations_pager_simple", function (require) {
        "use strict";

        var rpc = require("web.rpc");
        let isUpdating = false;

        function updateHistory(page) {
            if (isUpdating) {
                return;
            }

            const historyContainer = document.getElementById("donation_history_container");
            const pagerButtons = document.querySelectorAll("#history_pager_prev, #history_pager_next");

            if (!historyContainer) {
                console.error("Donation history container not found.");
                return;
            }

            isUpdating = true;
            pagerButtons.forEach((btn) => btn.classList.add("disabled"));

            rpc.query({
                route: "/my2/donations/history",
                params: {
                    invoice_page: page,
                },
            })
                .then(function (result) {
                    if (result.html) {
                        historyContainer.outerHTML = result.html;
                    }
                })
                .finally(() => {
                    isUpdating = false;
                    document.querySelectorAll("#history_pager_prev, #history_pager_next").forEach((btn) => {
                        if (btn) btn.classList.remove("disabled");
                    });
                });
        }

        document.addEventListener("click", function (event) {
            const btn = event.target.closest("#history_pager_prev, #history_pager_next");
            if (btn) {
                event.preventDefault();
                const page = btn.dataset.page;
                if (page) {
                    updateHistory(page);
                }
            }
        });

        document.addEventListener('open_payment_method_selector', function (ev) {
                var data = ev.detail || {};
                var $modal = $('#payment_method_selector_modal');

                var title = data.modal_type + ' Payment Method';
                $modal.find('#modal_title').text(title);

                // 2. Define Descriptions based on Type
                var descriptions = {
                    'Update': 'Update your payment method.',
                    'Add': 'Add a new payment method to your account.',
                    'Change': 'Change your payment method for ' + (data.child_name || 'your sponsored child') + '.',
                };
                // Set description
                $modal.find('#modal_description').text(descriptions[data.modal_type]);

                // Store other data (e.g., for form submission)
                $modal.data('group-id', data.group_id || false);
                $modal.data('contract-id', data.contract_id || false);
                // You can use these in your form logic, e.g., set hidden inputs
                $('#selected_contract_group_id').val($modal.data('group-id'));

                // Show the modal
                $modal.modal('show');
            });

            // Clean up on hide
            $('#payment_method_selector_modal').on('hidden.bs.modal', function () {
                $(this).removeData(['group-id', 'contract-id']);
                $('#modal_title').text('Payment Method');
                $('#modal_description').text('Select a payment method.');
            });
    });
});
