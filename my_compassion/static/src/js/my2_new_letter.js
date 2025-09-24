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

                const creationData = { ...formData, source: "mycompassion", csrf_token: odoo.csrf_token, mode: mode };

                if (mode === "send") {
                    $("#submitModal").modal({ backdrop: "static", keyboard: false }).modal("show");

                    const ProgressBarWidgetClass = publicWidget.registry.ProgressBarWidget;
                    this.progressBar = new ProgressBarWidgetClass(this, {
                        density: "medium",
                        steps: ["Creating your letter…"],
                    });
                    await this.progressBar.appendTo($("#progress-bar-div"));
                }

                try {
                    const initialResult = await this._submitLetterRPC(creationData);
                    if (!initialResult.generator_id) {
                        throw new Error(initialResult.error || "Could not create the letter record.");
                    }

                    this._launchProcessingRPC({
                        generator_id: initialResult.generator_id,
                        child_id: formData.child_id,
                        mode: mode,
                        csrf_token: odoo.csrf_token
                    });

                    // --- ROBUST FIX IS HERE ---
                    const updateProgress = (message) => {
                        if (this.progressBar && message) {
                            // This is a more robust way to update the text.
                            // It first tries the specific label, but if that fails,
                            // it updates the main widget element as a fallback.
                            const stepLabel = this.progressBar.$el.find(".progress-bar-step-label").first();
                            if (stepLabel.length) {
                                stepLabel.text(message);
                            } else {
                                // Fallback: If the specific label isn't found, update the whole component's text.
                                // This helps confirm if the polling data is being received.
                                this.progressBar.$el.text(message);
                            }
                        }
                    };

                    const processingPromise = this._pollForStatus(initialResult.generator_id, updateProgress);

                    const finalResult = await processingPromise;

                    await this._handleResponse(mode, finalResult, formData.child_id);

                } catch (error) {
                    if (this.progressBar) {
                        this.progressBar.destroy();
                    }
                    $("#submitModal").modal("hide");
                    ToastService.error(
                        error.message || "An error occurred while processing your letter. Please try again or contact the support."
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
                        warning = $('<div id="emoji-warning" style="color: red; margin-top: 5px;"></div>');
                        this.$("#letter-input").parent().append(warning);
                    }
                    warning.text("Emojis are not supported in letters.");
                    letterInput.value = cleanedValue;
                } else {
                    this.$("#emoji-warning").remove();
                }
            },

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

            _submitLetterRPC: function (data) {
                return rpc.query({
                    route: "/my2/children/letter/new",
                    params: data,
                });
            },

            _launchProcessingRPC: function (data) {
                return rpc.query({
                    route: "/my2/children/letter/launch_processing",
                    params: data,
                });
            },

            _pollForStatus: function (generatorId, onProgressUpdate) {
                return new Promise((resolve, reject) => {
                    const intervalId = setInterval(async () => {
                        try {
                            const response = await rpc.query({
                                route: "/my2/children/letter/status",
                                params: { generator_id: generatorId },
                            });

                            console.log("Polling status:", response.status);

                            if (onProgressUpdate && response.status) {
                                const friendlyMessage = response.status.charAt(0).toUpperCase() + response.status.slice(1) + '...';
                                onProgressUpdate(friendlyMessage);
                            }

                            if (response.status === 'done') {
                                clearInterval(intervalId);
                                resolve(response.result);
                            } else if (response.status === 'failed') {
                                clearInterval(intervalId);
                                reject(new Error(response.error || "Letter generation failed."));
                            }

                        } catch (error) {
                            clearInterval(intervalId);
                            reject(error);
                        }
                    }, 200);
                });
            },

            _handleResponse: function (mode, result, childId) {
                if (mode === "send") {
                    window.location.href = `/my2/children/letters/${childId}?new_letter_generator_id=${result.generator_id}`;
                } else if (mode === "preview") {
                    $("#previewImage").attr("src", result.preview_url);
                    $("#previewModal").modal("show");
                }
            },
        });

        return publicWidget.registry.NewLetterForm;
    });
});