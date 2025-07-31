/** @odoo-module **/
document.addEventListener("DOMContentLoaded", function () {
    odoo.define('my_compassion.user_settings', function (require) {
        "use strict";

        const rpc = require('web.rpc');

        const mobileSelect = document.getElementById('user-settings-tabs-mobile');
        const desktopTabs = document.getElementById('user-settings-tabs');
        const tabContent = document.querySelectorAll('.tab-content .tab-pane');
        const tabLinks = document.querySelectorAll('#user-settings-tabs .nav-link');
        const checkbox = document.getElementById('flexCheckDefault');

        // --------------
        // TAB NAVIGATION
        // --------------

        // Activate selected tab by ID
        function activateTab(tabId) {
            tabContent.forEach(tab => tab.classList.remove('show', 'active'));
            tabLinks.forEach(link => {
                link.classList.remove('active');
                link.setAttribute('aria-selected', 'false');
            });

            const selectedPane = document.querySelector(tabId);
            if (selectedPane) selectedPane.classList.add('show', 'active');

            const selectedLink = document.querySelector(`a[href="${tabId}"]`);
            if (selectedLink) {
                selectedLink.classList.add('active');
                selectedLink.setAttribute('aria-selected', 'true');
            }
        }

        // Handle mobile tab select
        mobileSelect?.addEventListener('change', function () {
            activateTab(this.value);
        });

        // Initialize active tab on load
        if (mobileSelect) {
            activateTab(mobileSelect.value);
        }

        // Sync tab selection with mobile dropdown
        tabLinks.forEach(link => {
            link.addEventListener('click', function () {
                if (mobileSelect) {
                    mobileSelect.value = this.getAttribute('href');
                }
            });
        });

        // ----------------
        // PRIVACY DATA TAB
        // ----------------
        checkbox?.addEventListener("change", function () {
            if (checkbox.checked) {
                const url = new URL(window.location);
                url.searchParams.set("sign_confirm", "true");
                window.location.href = url.toString();
            }
        });

        // --------------------------
        // COMMUNICATION SETTINGS TAB
        // --------------------------

        const comm_settings_tab_fields = {
            tax_preference_select: document.getElementById('tax_preference_select'),
            letter_preference_select: document.getElementById('letter_preference_select'),
            photo_preference_select: document.getElementById('photo_preference_select'),
            calendarCheck: document.getElementById('calendarCheck'),
            birthdaysCheck: document.getElementById('birthdaysCheck'),
            anniversaryCheck: document.getElementById('anniversaryCheck'),
        };

        Object.entries(comm_settings_tab_fields).forEach(([key, element]) => {
            if (!element) return;

            const isCheckbox = element.tagName === 'INPUT' && element.type === 'checkbox';
            const eventType = isCheckbox ? 'change' : 'input';

            element.addEventListener(eventType, () => {
                const rawValue = isCheckbox ? element.checked : element.value;
                const value = typeof rawValue === 'boolean' ? String(rawValue) : rawValue;

                const payload = {};
                switch (key) {
                    case 'tax_preference_select':
                        payload.tax_receipt_preference = value;
                        break;
                    case 'letter_preference_select':
                        payload.letter_delivery_preference = value;
                        break;
                    case 'photo_preference_select':
                        payload.photo_delivery_preference = value;
                        break;
                    case 'calendarCheck':
                        payload.calendar = value;
                        break;
                    case 'birthdaysCheck':
                        payload.birthday_reminder = value;
                        break;
                    case 'anniversaryCheck':
                        payload.sponsorship_anniversary_card = value;
                        break;
                    default:
                        return;
                }

                rpc.query({
                    route: "/my2/user_settings/set_communication_settings",
                    params: payload,
                }).catch((err) => {
                    console.error("RPC Error:", err);
                });
            });
        });

        // ------------------------
        // PERSONAL INFORMATION TAB
        // ------------------------

        const applyButton = document.getElementById("ApplyModificationsInfoButton");

        applyButton?.addEventListener("click", function (event) {
            event.preventDefault();

            const url = new URL("/my2/user_settings", window.location.origin);
            url.searchParams.set("submitted_info_edited", true);

            const fields = ["title", "surname", "name", "address", "city", "country_id", "zip", "phone", "email"];

            fields.forEach((field) => {
                const value = document.getElementById(field)?.value?.trim();
                if (value) {
                    url.searchParams.set(`${field}_change`, value);
                }
            });

            // Redirect with updated query parameters
            window.location.href = url.toString();
        });
    });
});
