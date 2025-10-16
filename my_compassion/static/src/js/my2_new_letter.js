/**
 * Handles the new_letter form submission.
 * Shows a progress bar that updates as the letter is processed by polling the server.
 * The update works by:
 * 1) Request the server to create a letter generation task, server returns a gen.Id.
 * and the maps to build the progress bar steps in the following format:
 * steps = [ [step_index, generation_status, step_description], ...]
 * 2) Tell the server to start processing the task while updating the task state.
 * 3) Poll the server to get the current statusof the task and update the progress bar accordingly.
 * 4) Once the task is complete, redirect or show a preview based on user choice.
 *
 * Is used in /templates/pages/my2_new_letter.xml
 *
 */
document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion", function (require) {
        "use strict";

        const publicWidget = require("web.public.widget");
        const rpc = require("web.rpc");
        const ToastService = require("my_compassion.toast_service");
        const _t = require("web.core")._t;

        publicWidget.registry.NewLetterForm = publicWidget.Widget.extend({
            selector: "#new_letter_form",

            events: {
                submit: "_onSubmitLetter",
                "input #letter-input": "_onLetterInput",
            },

            init: function () {
                this._super.apply(this, arguments);
                this.RE_EMOJI = /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g;
                this.progressBar = null;
            },

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

                try {
                    const initialResult = await this._createGenerator(creationData);
                    if (!initialResult.generator_id) {
                        throw new Error(initialResult.error || "Could not create the letter record.");
                    }

                    // --- Send Mode Logic ---
                    const steps = (initialResult.steps || []).map((step) => step[2]);
                    const statusMap = (initialResult.steps || []).reduce((map, step) => {
                        map[step[1]] = step[0];
                        return map;
                    }, {});

                    // 1. Create the widget object in memory BEFORE showing the modal.
                    const ProgressBarWidgetClass = publicWidget.registry.ProgressBarWidget;
                    this.progressBar = new ProgressBarWidgetClass(this, {
                        density: "medium",
                        steps: steps,
                    });

                    // 2. Use a Promise to wait for the modal and widget rendering to complete.
                    await new Promise((resolve) => {
                        const modal = $("#submitModal");
                        modal.one("shown.bs.modal", async () => {
                            // 3. The modal is now visible. Append the pre-made widget.
                            await this.progressBar.appendTo(modal.find("#progress-bar-div"));
                            this.progressBar.startProgress();
                            resolve(); // Continue the main function
                        });
                        // 4. Trigger the modal to show.
                        modal.modal({ backdrop: "static", keyboard: false }).modal("show");
                    });

                    // 5. With UI ready, launch and poll the backend task.
                    this._launchProcessingRPC({
                        generator_id: initialResult.generator_id,
                        child_id: formData.child_id,
                        mode: mode,
                        csrf_token: odoo.csrf_token,
                    }).catch((err) => console.error("Failed to launch letter generation:", err));

                    const updateProgress = (status) => {
                        if (this.progressBar && status in statusMap) {
                            this.progressBar.goToStep(statusMap[status]);
                        }
                    };
                    const processingPromise = this._pollForStatus(
                        {
                            generator_id: initialResult.generator_id,
                            child_id: formData.child_id,
                            mode: mode,
                            csrf_token: odoo.csrf_token,
                        },
                        updateProgress
                    );
                    const finalResult = await processingPromise;

                    await this._handleResponse(mode, finalResult, formData.child_id);
                } catch (error) {
                    if (this.progressBar) {
                        this.progressBar.destroy();
                    }
                    $("#submitModal").modal("hide");
                    ToastService.error(
                        error.message ||
                            _t(
                                "An error occurred while processing your letter. Please try again or contact the support."
                            )
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
                    warning.text(_t("Emojis are not supported in letters."));
                    letterInput.value = cleanedValue;
                } else {
                    this.$("#emoji-warning").remove();
                }
            },

            _collectFormData: async function () {
                const childId = this.$("#child-dropdown").val();
                const letterBody = this.$("#letter-input").val();
                const selectedTemplateImage = document.getElementById("selected-template");
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

            _createGenerator: function (data) {
                return rpc.query({
                    route: "/my2/children/letters/create_generator",
                    params: data,
                });
            },

            _launchProcessingRPC: function (data) {
                return rpc.query({
                    route: "/my2/children/letters/launch_generation",
                    params: data,
                });
            },

            _pollForStatus: function (data, onProgressUpdate) {
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
                            const response = await rpc.query({
                                route: "/my2/children/letters/status",
                                params: data,
                            });
                            if (onProgressUpdate) {
                                onProgressUpdate(response.status);
                            }

                            if (response.status === "done") {
                                if (this.progressBar) {
                                    const lastStep = this.progressBar.options.steps.length - 1;
                                    this.progressBar.goToStep(lastStep);
                                }
                                clearInterval(intervalId);
                                resolve(response.result);
                            } else if (response.status === "failed") {
                                clearInterval(intervalId);
                                reject(new Error(response.error || "Letter generation failed."));
                            }
                        } catch (error) {
                            clearInterval(intervalId);
                            reject(error);
                        }
                    }, POLLING_INTERVAL);
                });
            },

            /**
             * Handles the final response after a successful task.
             */
            _handleResponse: function (mode, result, childId) {
                if (mode === "send") {
                    // No cleanup needed here, the page will redirect and clear everything.
                    window.location.href = `/my2/children/letters/${childId}?new_letter_generator_id=${result.generator_id}`;
                } else if (mode === "preview") {
                    // On success for preview, hide the progress modal and destroy the widget.
                    // This ensures a clean state for the user's next action.
                    $("#submitModal").modal("hide");
                    if (this.progressBar) {
                        this.progressBar.destroy();
                        this.progressBar = null; // Clean up the reference.
                    }

                    $("#previewImage").attr("src", result.preview_url);
                    $("#previewModal").modal("show");
                } else if (mode === "save_draft") {
                    ToastService.success(result.message || _t("Draft saved!"));
                }
            },
        });

        return publicWidget.registry.NewLetterForm;
    });
});
