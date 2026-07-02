/** @odoo-module **/

/*
 * Handles the user settings page /my2/user_settings
 *
 * Is used in /templates/pages/my2_user_settings.xml
 */

import {rpc} from "@web/core/network/rpc";
import {whenReady} from "@odoo/owl";
import {toast} from "@my_compassion/js/toast_service";

/**
 * Main setup function to initialize all event listeners.
 */
function initializeUserSettings() {
  initTabNavigation();
  initCommunicationSettings();
  initAgreementsForm();
  initAccountDeletion();

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
  if (!desktopTabsContainer) {
    return;
  }

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
  } else if (tabLinks.length) activateTab(tabLinks[0].getAttribute("href"));

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
    let value = null;

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
      rpc("/my2/user_settings/set_communication_settings", {
        [field]: value,
      }).catch((err) => {
        console.error("RPC Error:", err);
        toast.error("Could not save your changes. Please try again.");
      });
    }
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
      rpc("/my2/user_settings/agree_data_protection", {})
        .then(() => {
          window.location.reload();
        })
        .catch((err) => {
          console.error("RPC Error:", err);
          toast.error("Could not save your confirmation. Please try again.");
        });
    } else {
      toast.error(
        "You must check the box to accept the legal terms and privacy policy before signing."
      );
    }
  });
}

function initAccountDeletion() {
  const checkbox = document.getElementById("ConfirmDeletionCheck");
  const confirmDeletionButton = document.getElementById("DeleteAccountFinalButton");

  if (!confirmDeletionButton) {
    return;
  }

  const standardView = document.querySelector("#deleteAccountModal .modal-body");
  const statusView = document.getElementById("deletion-status-view");
  const statusMessage = document.getElementById("deletion-progress-message");
  const continueButtonContainer = document.getElementById(
    "deletion-continue-button-container"
  );
  const continueButton = document.getElementById("DeleteAccountContinueButton");

  if (
    !standardView ||
    !statusView ||
    !statusMessage ||
    !continueButtonContainer ||
    !continueButton
  ) {
    console.error("Deletion modal elements not found. Aborting initAccountDeletion.");
    return;
  }

  confirmDeletionButton.addEventListener("click", () => {
    if (checkbox.checked) {
      Array.from(standardView.children).forEach((child) => {
        if (child.id !== "modal-title" && child.id !== "deletion-status-view") {
          child.classList.add("d-none");
        }
      });
      statusMessage.textContent = "The operation could require some minutes...";
      continueButtonContainer.classList.add("d-none");
      statusView.classList.remove("d-none");

      rpc("/my2/user_settings/delete_account", {})
        .then((response) => {
          if (response.success) {
            statusMessage.textContent = "Account deleted. You will be logged out.";
            window.location.href = "/web/session/logout";
          } else {
            statusMessage.textContent =
              "Sorry, the operation did not succeed. Please contact Compassion.";
            continueButtonContainer.classList.remove("d-none");
          }
        })
        .catch(() => {
          statusMessage.textContent =
            "An unexpected error occurred. Please try again later.";
          continueButtonContainer.classList.remove("d-none");
        });
    } else {
      toast.error(
        "Please check the box to confirm you understand this action cannot be undone."
      );
    }
  });

  continueButton.addEventListener("click", () => {
    statusView.classList.add("d-none");
    checkbox.checked = false;
    Array.from(standardView.children).forEach((child) => {
      if (child.id !== "modal-title" && child.id !== "deletion-status-view") {
        child.classList.remove("d-none");
      }
    });
  });
}

/**
 * Generic form handler for tabs with an "edit/save/cancel" workflow.
 */
function initFormHandler({
  formId,
  editButtonId,
  saveButtonId,
  cancelButtonId,
  endpoint,
  fields,
}) {
  const form = document.getElementById(formId);
  const editButton = document.getElementById(editButtonId);
  const saveButton = document.getElementById(saveButtonId);
  const cancelButton = document.getElementById(cancelButtonId);

  if (!form) {
    return;
  }

  if (!editButton || !saveButton || !cancelButton) {
    console.warn(`Handler not initialized for ${formId}. Missing element:`, {
      form,
      editButton,
      saveButton,
      cancelButton,
    });
    return;
  }

  const originalValues = {};

  const getFieldWidget = (fieldName) => {
    const input = form.querySelector(`[name="${fieldName}"]`);
    if (!input) return null;

    return $(input).closest(".form-field-component").data("widget");
  };

  function toggleLoader(isLoading) {
    const loader = document.getElementById("user-settings-loader");

    if (isLoading) {
      loader?.classList.remove("d-none");
    } else {
      loader?.classList.add("d-none");
    }
  }

  const showBackendErrors = (errors) => {
    for (const fieldName in errors) {
      const widget = getFieldWidget(fieldName);
      if (widget) {
        widget.showError(errors[fieldName]);
      } else {
        console.warn(
          `No widget found for field ${fieldName} to display error: ${errors[fieldName]}`
        );
      }
    }
  };

  const clearErrors = () => {
    fields.forEach((field) => {
      const widget = getFieldWidget(field);
      if (widget) {
        widget.clearError();
      }
    });
  };

  const validateForm = () => {
    let isValid = true;

    fields.forEach((field) => {
      const widget = getFieldWidget(field);
      if (widget) {
        if (!widget.validate()) {
          isValid = false;
        }
      }
    });

    return isValid;
  };

  const storeOriginalValues = () => {
    fields.forEach((field) => {
      const input = form.querySelector(`[name="${field}"]`);
      if (input)
        originalValues[field] = input.type === "checkbox" ? input.checked : input.value;
    });
  };

  const restoreOriginalValues = () => {
    fields.forEach((field) => {
      const input = form.querySelector(`[name="${field}"]`);
      if (input && originalValues[field] !== undefined) {
        if (input.type === "checkbox") {
          input.checked = originalValues[field];
        } else {
          input.value = originalValues[field];
        }
      }
    });
  };

  const anyValueUpdated = () => {
    return fields.some((field) => {
      const input = form.querySelector(`[name="${field}"]`);
      if (input) {
        const valueToCheck = input.type === "checkbox" ? input.checked : input.value;
        return valueToCheck !== originalValues[field];
      }
    });
  };

  const getRpcErrorMessage = (err, fallbackMessage) => {
    const messageArguments =
      err?.message?.data?.arguments ?? err?.data?.arguments ?? err?.message?.arguments;

    if (Array.isArray(messageArguments)) {
      const messages = messageArguments.filter(
        (item) => typeof item === "string" && item.trim()
      );
      if (messages.length) {
        return messages.join("\n");
      }
    }

    if (typeof messageArguments === "string" && messageArguments.trim()) {
      return messageArguments;
    }

    if (typeof err?.message === "string" && err.message.trim()) {
      return err.message;
    }

    return fallbackMessage;
  };

  function toggleEdit(isEditing) {
    clearErrors();
    form.classList.toggle("is-editing", isEditing);
  }

  editButton.addEventListener("click", (e) => {
    e.preventDefault();
    storeOriginalValues();
    toggleEdit(true);
  });

  cancelButton.addEventListener("click", (e) => {
    e.preventDefault();
    restoreOriginalValues();
    toggleEdit(false);
  });

  saveButton.addEventListener("click", (e) => {
    e.preventDefault();
    clearErrors();

    if (!validateForm()) return;
    toggleLoader(true);

    if (!anyValueUpdated()) {
      toggleLoader(false);
      toggleEdit(false);
      return;
    }

    const payload = {};
    for (const field of fields) {
      const input = form.querySelector(`[name="${field}"]`);
      if (!input || input.offsetParent === null) continue; // Skip hidden/missing inputs
      payload[field] = input.type === "checkbox" ? input.checked : input.value;
    }

    rpc(endpoint, payload)
      .then((response) => {
        if (response.success) {
          fields.forEach((field) => {
            const input = form.querySelector(`[name="${field}"]`);
            const displayEl = form.querySelector(`[data-display-for="${field}"]`);
            if (!input || !displayEl) return;

            displayEl.textContent =
              input.tagName === "SELECT"
                ? input.options[input.selectedIndex].text
                : input.value;
          });
          toggleEdit(false);
          toggleLoader(false);
        } else {
          if (response.errors) {
            showBackendErrors(response.errors);
          }
          toggleLoader(false);
        }
      })
      .catch((err) => {
        const fallbackMessage = "An unexpected error occurred. Please try again later.";
        const errorMessage = getRpcErrorMessage(err, fallbackMessage);
        console.error("RPC Error:", err);
        toast.error(errorMessage);
        toggleLoader(false);
      });
  });
}

whenReady(initializeUserSettings);
