document.addEventListener("DOMContentLoaded", function () {
    const mobileSelect = document.getElementById('user-settings-tabs-mobile');
    const desktopTabs = document.getElementById('user-settings-tabs');
    const tabContent = document.querySelectorAll('.tab-content .tab-pane');
    const tabLinks = document.querySelectorAll('#user-settings-tabs .nav-link');
    const checkbox = document.getElementById("flexCheckDefault");

    // --- PRIVACY DATA TAB ---
    checkbox?.addEventListener("change", function () {
        if (checkbox.checked) {
            const url = new URL(window.location);
            url.searchParams.set("sign_confirm", "true");
            window.location.href = url.toString();
        }
    });

    // --- COMMUNICATION SETTINGS TAB ---
    const commConfirmBtn = document.getElementById('ApplyModificationsCommButton');

    commConfirmBtn?.addEventListener('click', function () {
        const preferences = {
            tax_receipt_preference: document.getElementById('tax_preference_select')?.value,
            letter_delivery_preference: document.getElementById('letter_preference_select')?.value,
            photo_delivery_preference: document.getElementById('photo_preference_select')?.value,
            calendar: document.getElementById('calendarCheck')?.checked,
            birthday_reminder: document.getElementById('birthdaysCheck')?.checked,
            sponsorship_anniversary_card: document.getElementById('anniversaryCheck')?.checked,
        };

        const url = new URL(window.location);

        Object.entries(preferences).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.set(key, value);
            }
        });

        window.location.href = url.toString();
    });

    // --- PERSONAL INFORMATION TAB ---
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

    mobileSelect?.addEventListener('change', function () {
        activateTab(this.value);
    });

    if (mobileSelect) {
        activateTab(mobileSelect.value);
    }

    tabLinks.forEach(link => {
        link.addEventListener('click', function () {
            if (mobileSelect) {
                mobileSelect.value = this.getAttribute('href');
            }
        });
    });

    // --- SEND PERSONAL INFO MODIFICATIONS ---
    const applyButton = document.getElementById("ApplyModificationsInfoButton");

    applyButton?.addEventListener("click", function (event) {
        event.preventDefault();
        const url = new URL("/my2/user_settings", window.location.origin);
        url.searchParams.set("submitted_info_edited", true);

        const fields = ["title", "surname", "name", "address", "city", "zip", "phone", "email"];

        fields.forEach((field) => {
            const value = document.getElementById(field)?.value?.trim();
            if (value) {
                url.searchParams.set(`${field}_change`, value);
            }
        });

        window.location.href = url.toString();
    });
});
