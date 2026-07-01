/** @odoo-module **/

/**
 * Handles the new_letter form submission (save draft / preview / send).
 *
 * - Save draft persists the letter generator.
 * - Preview: the server renders the letter synchronously and returns its HTML,
 *   shown in the preview modal.
 * - Send: the server enqueues generation; an indeterminate progress bar runs while
 *   the generator state is polled, then the page redirects to the letters listing
 *   (the letter PDF renders lazily when viewed).
 *
 * Is used in /templates/pages/my2_new_letter.xml
 */

import {Component} from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";
import {mountComponent} from "@web/env";
import {_t} from "@web/core/l10n/translation";
import {toast} from "@my_compassion/js/toast_service";
import {letterAttachments} from "@my_compassion/js/my2_letter_attachments";
import {ProgressBar} from "@theme_compassion_2025/js/components/ProgressBar";

publicWidget.registry.NewLetterForm = publicWidget.Widget.extend({
  selector: "#new_letter_form",

  events: {
    submit: "_onSubmitLetter",
    "input #letter-input": "_onLetterInput",
  },

  init: function () {
    this._super.apply(this, arguments);
    this.RE_EMOJI =
      /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g;
    this.progressBarApp = null;
    this.lastDraft = null;
    this.autoSaveTimer = null;
  },

  start: function () {
    // On starting, bind the remove buttons to the existing attachments got from the draft loading
    const attachmentIds = $(".uploaded-file")
      .map(function () {
        return $(this).data("file-key");
      })
      .get();
    this._bindAttachmentToRemoveButton(attachmentIds);
  },

  _onSubmitLetter: async function (ev) {
    ev.preventDefault();

    const submitButton = ev.originalEvent.submitter;
    const mode = $(submitButton).data("custom");

    // Validation check for mode
    if (!["send", "preview", "save_draft"].includes(mode)) {
      return;
    }

    let formData = null;
    try {
      formData = await this._collectFormData();
    } catch (error) {
      toast.error(error.message);
      return;
    }

    const creationData = {
      ...formData,
      source: "mycompassion",
      csrf_token: odoo.csrf_token,
      mode: mode,
    };

    try {
      const initialResult = await this._createGenerator(creationData);

      if (!initialResult.generator_id) {
        throw new Error(initialResult.error || _t("Could not save the letter."));
      }
      if (mode === "save_draft") {
        this._handleResponse("save_draft", initialResult, formData.child_id);
        toast.success(_t("Letter saved!"));
        return;
      }

      if (mode === "preview") {
        // Show the server-rendered HTML letter in the preview modal.
        const previewResult = await this._launchProcessingRPC({
          generator_id: initialResult.generator_id,
          child_id: formData.child_id,
          mode: "preview",
          csrf_token: odoo.csrf_token,
        });
        this._showPreview(previewResult.preview_html);
        return;
      }

      // Send: show a progress bar while the letter is generated, poll until
      // it is ready, then open the letters listing.
      const modalEl = document.getElementById("submitModal");
      const modal = Modal.getOrCreateInstance(modalEl, {
        backdrop: "static",
        keyboard: false,
      });
      await new Promise((resolve) => {
        modalEl.addEventListener(
          "shown.bs.modal",
          async () => {
            const progressBarEl = modalEl.querySelector("#progress-bar-div");
            progressBarEl.replaceChildren();
            // Reuse the page's frontend env (Component.env); the
            // imperative mount requires it to share the page services.
            this.progressBarApp = await mountComponent(ProgressBar, progressBarEl, {
              env: Component.env,
              props: {steps: [_t("Sending your letter...")], flowing: true},
            });
            resolve();
          },
          {once: true}
        );
        modal.show();
      });

      this._launchProcessingRPC({
        generator_id: initialResult.generator_id,
        child_id: formData.child_id,
        mode: "send",
        csrf_token: odoo.csrf_token,
      }).catch((err) => console.error("Failed to launch letter generation:", err));

      const finalResult = await this._pollForStatus({
        generator_id: initialResult.generator_id,
        child_id: formData.child_id,
      });
      this._handleResponse("send", finalResult, formData.child_id);
    } catch (error) {
      if (this.progressBarApp) {
        this.progressBarApp.destroy();
        this.progressBarApp = null;
      }
      Modal.getOrCreateInstance(document.getElementById("submitModal")).hide();
      toast.error(
        error.message ||
          _t(
            "An error occurred while processing your letter. Please try again or contact the support."
          )
      );
    }
  },

  _onLetterInput: function (ev) {
    const autosave_delay = 5000;

    const letterInput = ev.currentTarget;
    const originalValue = letterInput.value;
    const cleanedValue = originalValue.replace(this.RE_EMOJI, "");

    if (originalValue !== cleanedValue) {
      let warning = this.$("#emoji-warning");
      if (!warning.length) {
        warning = $(
          '<div id="emoji-warning" style="color: red; margin-top: 5px;"></div>'
        );
        this.$("#letter-input").parent().append(warning);
      }
      warning.text(_t("Emojis are not supported in letters."));
      letterInput.value = cleanedValue;
    } else {
      this.$("#emoji-warning").remove();
    }
    clearTimeout(this.autoSaveTimer);
    this.autoSaveTimer = setTimeout(() => {
      this._autoSaveDraft();
    }, autosave_delay);
  },

  _collectFormData: async function () {
    const childId = this.$("#child-dropdown").val();
    const letterBody = this.$("#letter-input").val();
    let templateId = this.$("#selected-template").attr("data-template-id") || null;
    if (!templateId) {
      const draftTemplate = document.getElementById("draft-template-id");
      templateId = draftTemplate ? draftTemplate.value : null;
    }
    const fileInput = this.$("#letter-attachments")[0];
    const generatorId = this.$("input[name='generator_id']").val();

    if (!childId) throw new Error(_t("Please select a child to write to."));
    if (!templateId) throw new Error(_t("Please select a template for your letter."));
    if (!letterBody) throw new Error(_t("Please write something in your letter."));

    const attachments = await this._encodeAttachments(fileInput.files);

    return {
      child_id: childId,
      template_id: templateId,
      letter_body: letterBody,
      attachments: attachments,
      generator_id: generatorId,
    };
  },

  _encodeAttachments: async function (fileList) {
    const filePromises = Array.from(fileList).map(
      (file) =>
        new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(file);
          reader.onload = () =>
            resolve({
              filename: file.name,
              content: reader.result.split(",")[1],
            });
          reader.onerror = () => reject(_t("Error reading file."));
        })
    );
    return Promise.all(filePromises);
  },

  _createGenerator: async function (data) {
    // Clear the uploaded files buffer as they are now sent to the server
    // This ensures that if multiple _creategenerator happen at once, the attachment list is coherent regardless of the time taken by the rpc query
    letterAttachments.files = [];
    const fileInput = this.$("#letter-attachments")[0];
    fileInput.value = "";

    const result = await rpc("/my2/children/letters/create_generator", data);
    // Bind the remove attachment buttons to the newly created attachment IDs
    // This ensures that any attachments saved on the server can be removed by the user.
    this._bindAttachmentToRemoveButton(result.image_ids || []);
    // Update the generator_id in the form to the lastest generated by the server for the current letter.
    this.$("input[name='generator_id']").val(result.generator_id || "");

    return result;
  },

  _launchProcessingRPC: function (data) {
    return rpc("/my2/children/letters/launch_generation", data);
  },

  _pollForStatus: function (data) {
    const POLLING_INTERVAL = 400;
    const MAX_POLLS = 150; // 400ms * 150 = 1 minute timeout
    let pollCount = 0;

    return new Promise((resolve, reject) => {
      const intervalId = setInterval(async () => {
        if (++pollCount > MAX_POLLS) {
          clearInterval(intervalId);
          reject(new Error("Letter generation timed out."));
          return;
        }
        try {
          const response = await rpc("/my2/children/letters/status", data);
          if (response.status === "done") {
            clearInterval(intervalId);
            resolve(response.result);
          }
          // Any non-done status keeps polling until MAX_POLLS.
        } catch (error) {
          clearInterval(intervalId);
          reject(error);
        }
      }, POLLING_INTERVAL);
    });
  },

  /**
   * Render the synchronous HTML preview in the preview modal.
   */
  _showPreview: function (previewHtml) {
    document.getElementById("previewImage").srcdoc = previewHtml || "";
    Modal.getOrCreateInstance(document.getElementById("previewModal")).show();
  },

  /**
   * Handles the final response after a successful task.
   */
  _handleResponse: function (mode, result, childId) {
    if (mode === "send") {
      // No cleanup needed here, the page will redirect and clear everything.
      window.location.href = `/my2/children/letters/${childId}?new_letter_generator_id=${result.generator_id}`;
    } else if (mode === "save_draft") {
      toast.success(result.message || "Draft saved!");
    }
  },
  _autoSaveDraft: async function () {
    try {
      const formData = await this._collectFormData();
      const currentDraft = JSON.stringify(formData);
      if (this.lastDraft === currentDraft) return;
      this.lastDraft = currentDraft;

      const data = {
        ...formData,
        source: "mycompassion",
        csrf_token: odoo.csrf_token,
        mode: "save_draft",
      };
      const result = await this._createGenerator(data);
      this._handleResponse("save_draft", result, formData.child_id);
    } catch (error) {
      console.warn("Auto-save draft failed:", error.message);
    }
  },

  /**
   * Binds the remove-attachment buttons' click event to the uploaded files.
   * @param {Array<number>} attachmentIds - A list of attachment IDs.
   */
  _bindAttachmentToRemoveButton: function (attachmentIds) {
    // Select all .uploaded-file elements
    const uploadedFilesEl = this.$(".uploaded-file");
    uploadedFilesEl.each((index, element) => {
      // Find the button within this element
      const $button = this.$(element).find(".remove-attachment-button");

      // Get the corresponding attachment ID from the input array
      // The ids necessarily match the increasing order of the .uploaded-file elements
      const attachmentId = attachmentIds[index];

      // Set the data attribute on the PARENT element
      element.dataset.fileKey = attachmentId;

      // Set the button to send a remove_attachment request on click
      // .off() prevents binding multiple click events if this function is called again
      $button.off("click").on("click", async (event) => {
        event.preventDefault();
        const idToRemove = element.getAttribute("data-file-key");

        if (!idToRemove) {
          const msg = _t("Attachment ID is missing.");
          toast.error(msg);
          return;
        }

        try {
          // Call Odoo route
          const result = await rpc("/my2/letter/remove_attachment", {
            attachment_id: parseInt(idToRemove, 10),
          });

          // Check server response
          if (result.success) {
            // Remove the entire '.uploaded-file' element
            element.remove();
          } else {
            const msg =
              result.error || _t("Error occurred while removing the attachment.");
            console.error("Server error:", msg, result);
            toast.error(msg);
          }
        } catch (error) {
          console.error("JS error while removing attachment:", error);
          toast.error(_t("Unable to remove the attachment."));
        }
      });
    });
  },
});
