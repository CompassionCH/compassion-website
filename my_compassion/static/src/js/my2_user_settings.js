document.addEventListener("DOMContentLoaded", function () {
    const mobileSelect = document.getElementById('user-settings-tabs-mobile');
    const desktopTabs = document.getElementById('user-settings-tabs');
    const tabContent = document.querySelectorAll('.tab-content .tab-pane');
    const tabLinks = document.querySelectorAll('#user-settings-tabs .nav-link');

    // Handles mobile tab content switching on page load and on dropdown change
    function activateTab(tabId) {
        tabContent.forEach(tab => tab.classList.remove('show', 'active'));
        tabLinks.forEach(link => {
            link.classList.remove('active');
            link.setAttribute('aria-selected', 'false');
        });

        const selectedPane = document.querySelector(tabId);
        if (selectedPane) {
            selectedPane.classList.add('show', 'active');
        }

        const selectedLink = document.querySelector(`a[href="${tabId}"]`);
        if (selectedLink) {
            selectedLink.classList.add('active');
            selectedLink.setAttribute('aria-selected', 'true');
        }
    }

    if (mobileSelect) {
        mobileSelect.addEventListener('change', function () {
            activateTab(this.value);
        });

        activateTab(mobileSelect.value);
    }

    tabLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            if (mobileSelect) {
                mobileSelect.value = this.getAttribute('href');
            }
        });
    });

    // Send wanted personal informations modifications to the backend
    const applyButton = document.getElementById("ApplyModificationsInfoButton");

    if (applyButton) {
        applyButton.addEventListener("click", function (event) {
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
    }
});