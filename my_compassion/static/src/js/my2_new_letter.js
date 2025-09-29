/**
 * Handles the new_letter form submission.
 *Shows a progress bar that updates as the letter is processed by polling the server.
 * The update works by:
 *    1) Request the server to create a letter generation task.
 *    2) Tell the server to start processing the task while updating the task state.
 *    3) Poll the server to get the current statusof the task and update the progress bar accordingly.
 *    4) Once the task is complete, redirect or show a preview based on user choice.
 *
 *Is used in /templates/pages/my2_new_letter.xml
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

            init: function () {
                this._super.apply(this, arguments);
                this.RE_EMOJI = /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g;
                this.progressBar = null;
            },

            _onSubmitLetter: async function (ev) {
                ev.preventDefault();

                const submitButton = ev.originalEvent.submitter;
                const mode = $(submitButton).data("custom");

                // Progress bar steps and status map
                const steps = [
                    "Creating Task...", // Step 0
                    "Applying Template...", // Step 1
                    "Adding Your Text...", // Step 2
                    "Adding Attachments...", // Step 3
                    "Generating PDF...", // Step 4
                    "Finalizing...", // Step 5
                ];
                const statusMap = {
                    create_task: 0,
                    apply_template: 1,
                    apply_text: 2,
                    apply_images: 3,
                    generate_pdf: 4,
                    finalizing: 5,
                };

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
                        steps: steps, // Use the steps defined above
                    });
                    await this.progressBar.appendTo($("#progress-bar-div"));

                    this.progressBar.startProgress();
                }
                //Ask the server to create a letter generation task
                try {
                    const initialResult = await this._createGenerator(creationData);
                    if (!initialResult.generator_id) {
                        throw new Error(initialResult.error || "Could not create the letter record.");
                    }
                    //Tell the server to start processing the task while updating the task state
                    this._launchProcessingRPC({
                        generator_id: initialResult.generator_id,
                        child_id: formData.child_id,
                        mode: mode,
                        csrf_token: odoo.csrf_token,
                    });

                    // Poll the state of the task and update the progress bar accordingly
                    const updateProgress = (status) => {
                        if (this.progressBar && status in statusMap) {
                            const stepIndex = statusMap[status];
                            this.progressBar.goToStep(stepIndex);
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

            // Ask the server to create a letter generation task and to return a generator_id
            _createGenerator: function (data) {
                return rpc.query({
                    route: "/my2/children/letters/create_generator",
                    params: data,
                });
            },
            // Tell the server to start processing the task while updating the task state
            // data contains generator_id, child_id, mode, csrf_token
            _launchProcessingRPC: function (data) {
                return rpc.query({
                    route: "/my2/children/letters/launch_generation",
                    params: data,
                });
            },

            // Poll the server to get the current status of the task and update the progress bar accordingly
            _pollForStatus: function (data, onProgressUpdate) {
                return new Promise((resolve, reject) => {
                    const intervalId = setInterval(async () => {
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
                    }, 400);
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
