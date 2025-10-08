/**
 * Handles the new_letter form submission.
 * Is used in /templates/pages/my2_new_letter.xml
 *
 */
document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion", function (require) {
        "use strict";

        const publicWidget = require("web.public.widget");
        const rpc = require("web.rpc");
        const ToastService = require("my_compassion.toast_service");

        publicWidget.registry.NewLetterForm = publicWidget.Widget.extend({
            selector: "#new_letter_form",

            events: {
                submit: "_onSubmitLetter",
                "input #letter-input": "_onLetterInput",
            },

            /**
             * @override
             */
            init: function () {
                this._super.apply(this, arguments);
                this.RE_EMOJI = /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g;
                this.progressBar = null;
            },

            /**
             * Handles the submission of the letter creation form. This function manages Preview and Submit mode
             *
             * @async
             * @function
             * @param {Event} event - The form submission event.
             *
             * @returns {Promise<void>} Resolves once the letter submission process is complete.
             */
            _onSubmitLetter: async function (ev) {
                ev.preventDefault();

                const submitButton = ev.originalEvent.submitter;
                const mode = $(submitButton).data("custom");

                let formData;
                try {
                    formData = await this._collectFormData();
                } catch (error) {
                    ToastService.error(error.message);
                    return;
                }

                const data = { ...formData, source: "mycompassion", csrf_token: odoo.csrf_token, mode: mode };
                let fakeProgressPromise;

                // If the mode is 'send', show a modal with a fake progress bar
                if (mode === "send") {
                    $("#submitModal").modal({ backdrop: "static", keyboard: false }).modal("show");

                    // Progress bar
                    const ProgressBarWidgetClass = publicWidget.registry.ProgressBarWidget;
                    this.progressBar = new ProgressBarWidgetClass(this, {
                        density: "medium",
                        steps: [
                            "Creating your letter…",
                            "Applying the template…",
                            "Adding your text…",
                            "Adding your attachments…",
                        ],
                    });
                    await this.progressBar.appendTo($("#progress-bar-div"));

                    fakeProgressPromise = this.progressBar.startProgress();
                }

                const rpcPromise = this._submitLetterRPC(data);

                try {
                    const [result] = await Promise.all([rpcPromise, fakeProgressPromise || Promise.resolve()]);
                    await this._handleResponse(mode, result, formData.child_id);
                } catch (error) {
                    if (this.progressBar) {
                        this.progressBar.destroy();
                    }
                    $("#submitModal").modal("hide");
                    ToastService.error(
                        "An error occurred while processing your letter. Please try again or contact the support."
                    );
                }
            },

            _onLetterInput: function (ev) {
                const letterInput = ev.currentTarget;
                const originalValue = letterInput.value;
                const cleanedValue = originalValue.replace(this.RE_EMOJI, "");

                if (originalValue !== cleanedValue) {
                    let warning = this.$("#emoji-warning");
                    if (!warning.length) {
                        // TODO refactor the styling with a class from the theme when theme is ready
                        warning = $('<div id="emoji-warning" style="color: red; margin-top: 5px;"></div>');
                        this.$("#letter-input").parent().append(warning);
                    }
                    warning.text("Emojis are not supported in letters.");
                    letterInput.value = cleanedValue;
                } else {
                    this.$("#emoji-warning").remove();
                }
            },

            /**
             * Collects and prepares all data from the letter submission form.
             *
             * This function extracts the selected child ID, letter content,
             * selected template ID (from the chosen image), and file attachments
             * from the form. It also encodes the attachments into base64 format.
             *
             * @async
             * @function
             * @returns {Promise<Object>} A promise that resolves to an object containing:
             *   @property {string} childId - The ID of the selected child.
             *   @property {string|null} templateId - The ID of the selected template, or null if not selected.
             *   @property {string} letterBody - The body text of the letter.
             *   @property {Array<{filename: string, content: string}>} attachments - The list of base64-encoded attachments.
             */
            _collectFormData: async function () {
                const childId = this.$("#child-dropdown").val();
                const letterBody = this.$("#letter-input").val();
                const templateId = this.$("#selected-template").attr("data-template-id") || null;
                const fileInput = this.$("#letter-attachments")[0];
                const attachments = await this._encodeAttachments(fileInput.files);

                if (!childId) throw new Error("Please select a child to write to.");
                if (!templateId) throw new Error("Please select a template for your letter.");
                if (!letterBody) throw new Error("Please write something in your letter.");

                return {
                    child_id: childId,
                    template_id: templateId,
                    letter_body: letterBody,
                    attachments: attachments,
                };
            },

            /**
             * Encodes a list of files into base64 format for backend transmission.
             *
             * This function takes a FileList (from an input[type="file"]) and returns
             * an array of objects, each containing the original filename and its content
             * as a base64-encoded string (excluding the MIME prefix).
             *
             * @async
             * @function
             * @param {FileList} fileList - The list of files selected by the user.
             * @returns {Promise<Array<{filename: string, content: string}>>}
             *   A promise resolving to an array of attachment objects with:
             *   - filename: Original name of the file.
             *   - content: Base64-encoded string (without the data URI prefix).
             */

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
                            reader.onerror = () => reject("Error reading file.");
                        })
                );
                return Promise.all(filePromises);
            },

            /**
             * Sends the letter form data to the backend via RPC.
             *
             * The backend is expected to return a preview URL (in preview mode)
             * and a generator ID for redirection (in send mode).
             *
             * @function
             * @param {Object} data - The data payload to send with the request.
             *
             * @returns {Promise<Object>} A promise that resolves with the backend response.
             */
            _submitLetterRPC: function (data) {
                return rpc.query({
                    route: "/my2/children/letters/new",
                    params: data,
                });
            },

            /**
             * Handles the server response after submitting or previewing a letter.
             *
             * Depending on the mode, this function either redirects the user to the letters
             * page with a reference to the newly created generator, or displays a preview
             * image of the letter in a modal dialog.
             *
             * @async
             * @function
             * @param {string} mode - Submission mode: `'send'` to submit the letter, `'preview'` to show a preview.
             * @param {Object} result - The result object returned by the server.
             * @param {string} childId - The ID of the selected child, used in the redirect URL.
             *
             * @returns {Promise<void>} Resolves when the UI navigation or update is complete.
             */
            _handleResponse: function (mode, result, childId) {
                if (mode === "send") {
                    window.location.href = `/my2/children/letters/${childId}`;
                } else if (mode === "preview") {
                    $("#previewImage").attr("src", result.preview_url);
                    $("#previewModal").modal("show");
                }
            },
        });

        return publicWidget.registry.NewLetterForm;
    });
});
