/**
 * Handles the user settings page /my2/user_settings
 *
 * Is used in /templates/pages/my2_user_settings.xml
 */

/** @odoo-module **/
document.addEventListener("DOMContentLoaded", () => {
    odoo.define("my_compassion.user_settings", function (require) {
        "use strict";

        const rpc = require("web.rpc");
        const Dialog = require("web.Dialog");

        /**
         * Main setup function to initialize all event listeners.
         */
        function initializeUserSettings() {
            // Hides the error messages of the select components
            document.querySelectorAll(".invalid-hint").forEach((hint) => {
                hint.style.display = "none";
            });

            initTabNavigation();
            initCommunicationSettings();
            initAgreementsForm();

            initFormHandler({
                formId: "personal-information-form",
                editButtonId: "EditInfoButton",
                saveButtonId: "ApplyModificationsInfoButton",
                cancelButtonId: "CancelModificationsInfoButton",
                endpoint: "/my2/user_settings/set_personal_info",
                fields: [
                    "title",
                    "lastname",
                    "firstname",
                    "street",
                    "city",
                    "country_id",
                    "zip",
                    "phone",
                    "mobile",
                    "email",
                ],
            });

            initFormHandler({
                formId: "account-settings-form",
                editButtonId: "EditAccountButton",
                saveButtonId: "ApplyModificationsAccountButton",
                cancelButtonId: "CancelModificationsAccountButton",
                endpoint: "/my2/user_settings/set_account_settings",
                fields: ["login"],
            });
        }

        /**
         * Handles the tab navigation logic for both mobile and desktop.
         */
        function initTabNavigation() {
            const mobileSelect = document.getElementById("user-settings-tabs-mobile");
            const desktopTabsContainer = document.getElementById("user-settings-tabs");
            const tabPanes = document.querySelectorAll(".tab-content .tab-pane");
            const tabLinks = document.querySelectorAll("#user-settings-tabs .nav-link");

            const activateTab = (targetId) => {
                tabPanes.forEach((pane) => pane.classList.remove("show", "active"));
                tabLinks.forEach((link) => link.classList.remove("active"));

                const targetPane = document.querySelector(targetId);
                const targetLink = document.querySelector(`a.nav-link[href="${targetId}"]`);

                if (targetPane) targetPane.classList.add("show", "active");
                if (targetLink) targetLink.classList.add("active");
                if (mobileSelect && mobileSelect.value !== targetId) mobileSelect.value = targetId;

                const url = new URL(window.location);
                url.searchParams.set("current_tab", targetId.substring(1));
                window.history.pushState({}, "", url);
            };

            const urlParams = new URLSearchParams(window.location.search);
            const currentTab = urlParams.get("current_tab");
            if (currentTab) {
                activateTab(`#${currentTab.replace(/\s+/g, "-")}`);
            } else {
                if (tabLinks.length) activateTab(tabLinks[0].getAttribute("href"));
            }

            desktopTabsContainer?.addEventListener("click", (e) => {
                if (e.target.matches("a.nav-link")) {
                    e.preventDefault();
                    activateTab(e.target.getAttribute("href"));
                }
            });

            mobileSelect?.addEventListener("change", (e) => activateTab(e.target.value));
        }

        /**
         * Initializes the immediate-update logic for communication settings.
         */
        function initCommunicationSettings() {
            const container = document.getElementById("communication-settings");
            if (!container) return;
            container.addEventListener("change", (e) => {
                const target = e.target;
                // Skip if the event is not on an input or select
                if (!target.matches("input, select")) return;
                let field = target.dataset.field;
                let value;

                if (!field && target.tagName === "SELECT") {
                    switch (target.id) {
                        case "letter_preference_select":
                            field = "letter_delivery_preference";
                            break;
                        case "photo_preference_select":
                            field = "photo_delivery_preference";
                            break;
                        case "tax_preference_select":
                            field = "tax_certificate";
                            break;
                    }
                }
                // Determine the value based on element type
                if (target.type === "checkbox") {
                    value = target.checked;
                    // Handle inverted logic for opt_out
                    if (field === "opt_out") {
                        value = !value;
                    }
                } else {
                    value = target.value;
                }
                // If we have a field, send the update
                if (field) {
                    rpc.query({
                        route: "/my2/user_settings/set_communication_settings",
                        params: { [field]: value },
                    }).catch((err) => {
                        console.error("RPC Error:", err);
                        Dialog.alert(null, "Could not save your changes. Please try again.");
                    });
                }
            });
        }

        /**
         * Attaches a standardized event listener to an agreement checkbox.
         * When checked, it calls a specific RPC route.
         */

        function attachAgreementListener(checkbox, route) {
            checkbox.addEventListener("change", function () {
                // Only proceed if the checkbox is being checked
                if (!this.checked) return;

                rpc.query({ route, params: {} })
                    .then(() => {
                        window.location.reload();
                    })
                    .catch((err) => {
                        console.error("RPC Error:", err);
                        this.checked = false; // Revert the checkbox state on error
                        Dialog.alert(null, "Could not save your confirmation. Please try again.");
                    });
            });
        }

        /**
         * Initializes the privacy checkbox.
         */
        function initAgreementsForm() {
            const signButton = document.getElementById("SignLegalAgreementButton");
            const checkbox = document.getElementById("LegalAgreementCheck");

            if (!signButton || !checkbox) {
                return;
            }

            signButton.addEventListener("click", () => {
                if (checkbox.checked) {
                    rpc.query({
                        route: "/my2/user_settings/agree_data_protection",
                        params: {},
                    })
                        .then(() => {
                            window.location.reload();
                        })
                        .catch((err) => {
                            console.error("RPC Error:", err);
                            Dialog.alert(null, "Could not save your confirmation. Please try again.");
                        });
                } else {
                    Dialog.alert(
                        null,
                        "You must check the box to accept the legal terms and privacy policy before signing."
                    );
                }
            });
        }

        /**
         * Generic form handler for tabs with an "edit/save/cancel" workflow.
         */
        function initFormHandler({ formId, editButtonId, saveButtonId, cancelButtonId, endpoint, fields }) {
            const form = document.getElementById(formId);
            const editButton = document.getElementById(editButtonId);
            const saveButton = document.getElementById(saveButtonId);
            const cancelButton = document.getElementById(cancelButtonId);

            if (!form || !editButton || !saveButton || !cancelButton) {
                console.warn(`Handler not initialized for ${formId}. Missing element:`, {
                    form,
                    editButton,
                    saveButton,
                    cancelButton,
                });
                return;
            }

            let originalValues = {};

            const clearErrors = () => {
                form.querySelectorAll(".is-invalid").forEach((input) => {
                    input.classList.remove("is-invalid");
                });
                form.querySelectorAll(".invalid-hint").forEach((hint) => {
                    hint.style.display = "none";
                });
            };

            const showErrors = (errors) => {
                for (const fieldName in errors) {
                    const input = form.querySelector(`[name="${fieldName}"]`);
                    if (input) {
                        input.classList.add("is-invalid");
                        const container = input.closest(".form-field-container");
                        if (container) {
                            const hintEl = container.querySelector(".invalid-hint");
                            if (hintEl) {
                                hintEl.textContent = errors[fieldName];
                                hintEl.style.display = "block";
                            }
                        }
                    }
                }
            };

            const storeOriginalValues = () => {
                fields.forEach((field) => {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input) originalValues[field] = input.value;
                });
            };

            const restoreOriginalValues = () => {
                fields.forEach((field) => {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input && originalValues[field] !== undefined) {
                        input.value = originalValues[field];
                    }
                });
            };

            editButton.addEventListener("click", () => {
                storeOriginalValues();
                clearErrors();
                form.classList.add("is-editing");
            });

            cancelButton.addEventListener("click", () => {
                restoreOriginalValues();
                clearErrors();
                form.classList.remove("is-editing");
            });

            saveButton.addEventListener("click", () => {
                clearErrors();
                const payload = {};
                fields.forEach((field) => {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input) payload[field] = input.value;
                });

                rpc.query({ route: endpoint, params: payload })
                    .then((response) => {
                        if (response.success) {
                            fields.forEach((field) => {
                                const input = form.querySelector(`[name="${field}"]`);
                                const displayEl = form.querySelector(`[data-display-for="${field}"]`);
                                if (!input || !displayEl) return;

                                displayEl.textContent =
                                    input.tagName === "SELECT" ? input.options[input.selectedIndex].text : input.value;
                            });
                            form.classList.remove("is-editing");
                        } else {
                            if (response.errors) {
                                showErrors(response.errors);
                            }
                        }
                    })
                    .catch((err) => {
                        console.error("RPC Error:", err);
                        Dialog.alert(null, "An unexpected error occurred. Please try again later.");
                    });
            });
        }

        initializeUserSettings();
    });
});
