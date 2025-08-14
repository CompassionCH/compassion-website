/**
 * Handles the new_letter form submission.
 * Is used in /templates/pages/my2_new_letter.xml
 *
 */
document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion", function (require) {
        "use strict";

        // Import necessary modules (here we need the ToastService for notifications)
        const ToastService = require("my_compassion.toast_service");
        const rpc = require("web.rpc");

        const form = document.querySelector("form");
        if (form) {
            form.addEventListener("submit", onSubmitLetter);
        }
        const letterInput = document.getElementById("letter-input");
        const RE_EMOJI = /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g;

        if (letterInput) {
            letterInput.addEventListener("input", function () {
                const originalValue = letterInput.value;
                const cleanedValue = originalValue.replace(RE_EMOJI, "");

                if (originalValue !== cleanedValue) {
                    let warning = document.getElementById("emoji-warning");
                    if (!warning) {
                        warning = document.createElement("div");
                        warning.id = "emoji-warning";
                        // TODO refactor the styling with a class from the theme when theme is ready
                        warning.style.color = "red";
                        warning.style.marginTop = "5px";
                        letterInput.parentNode.appendChild(warning);
                    }
                    warning.textContent = "Emojis are not supported in letters.";
                    letterInput.value = cleanedValue;
                } else {
                    const warning = document.getElementById("emoji-warning");
                    if (warning) {
                        warning.remove();
                    }
                }
            });
        }

        /**
         * Handles the submission of the letter creation form. This function manages Preview and Submit mode
         *
         * @async
         * @function
         * @param {Event} event - The form submission event.
         *
         * @returns {Promise<void>} Resolves once the letter submission process is complete.
         */
        async function onSubmitLetter(event) {
            // Prevent default form submission to handle the process manually
            event.preventDefault();

            // Get the button that triggered the form submission (either Preview or Submit)
            const submitButton = event.submitter;
            const mode = $(submitButton).data("custom");

            // Collect the form data
            let childId, templateId, letterBody, attachments;
            try {
                ({ childId, templateId, letterBody, attachments } = await collectFormData());
            } catch (error) {
                ToastService.error(error.message);
                return;
            }

            // Prepare the data to send to the backend
            const data = {
                child_id: childId,
                template_id: templateId,
                letter_body: letterBody,
                source: "mycompassion",
                csrf_token: odoo.csrf_token,
                attachments: attachments,
                mode: mode,
            };

            let fakeProgressPromise;
            let timeoutId;

            // If the mode is 'send', show a modal with a fake progress bar
            if (mode === "send") {
                // Show the modal and prevents the user to be able to close the modal
                $("#submitModal")
                    .modal({
                        backdrop: "static",
                        keyboard: false,
                    })
                    .modal("show");

                const progressControl = showFakeProgress();
                fakeProgressPromise = progressControl.promise;
                timeoutId = progressControl.timeoutId;
            }

            // Send the data to the server using RPC, either with send or preview mode.
            const rpcPromise = submitLetterRPC(data);

            try {
                // Promise.race waits for the first promise to settle (either resolves or rejects)
                await Promise.race([
                    // The RPC request promise
                    rpcPromise.catch((err) => {
                        throw err;
                    }),
                    // If no fake progress is needed (in preview mode),
                    // use Promise.resolve() to ensure Promise.race always has a valid promise.
                    fakeProgressPromise || Promise.resolve(),
                ]);

                const result = await rpcPromise;
                // Wait for the fake progress to even if backend response was faster
                // (Yes this is an anti-pattern, I'm sorry, I need to rush)
                if (fakeProgressPromise) await fakeProgressPromise;
                await handleResponse(mode, result, childId);
            } catch (error) {
                // Remove the modal with the fake progress bar in case of error
                if (timeoutId) clearTimeout(timeoutId);
                $("#submitModal").modal("hide");
                ToastService.error(
                    "An error occurred while processing your letter. Please try again or contact the support."
                );
                return;
            }
        }

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
        async function collectFormData() {
            const childId = document.getElementById("child-dropdown").value;
            const letterBody = document.getElementById("letter-input").value;

            const selectedTemplateImage = document.getElementById("selected-template");
            const templateId = selectedTemplateImage ? selectedTemplateImage.getAttribute("data-template-id") : null;

            const fileInput = document.getElementById("letter-attachments");

            // TODO handle in a clean way encoding potential issue with a throw new Error
            const attachments = await encodeAttachments(fileInput.files);

            // Validate inputs and throw error messages in case of missing value
            if (!childId) {
                throw new Error("Please select a child to write to.");
            }

            if (!templateId) {
                throw new Error("Please select a template for your letter.");
            }

            if (!letterBody) {
                throw new Error("Please write something in your letter");
            }

            return { childId, templateId, letterBody, attachments };
        }

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
        async function encodeAttachments(fileList) {
            const filePromises = Array.from(fileList).map((file) => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.readAsDataURL(file);
                    reader.onload = () => {
                        resolve({
                            filename: file.name,
                            content: reader.result.split(",")[1],
                        });
                    };
                    reader.onerror = () => reject("Error reading file.");
                });
            });

            try {
                return await Promise.all(filePromises);
            } catch (error) {
                ToastService.error(
                    "An error occurred while processing attachments. Please try again or contact the support."
                );
                return [];
            }
        }

        /**
         * Simulates a multi-step progress indicator for letter submission.
         *
         * This function fakes progress feedback for the user interface by sequentially
         * updating a progress bar and text element with predefined steps (e.g., "Sending your letter information…").
         * Each step is displayed for 1 second before moving to the next, giving the illusion of work being done.
         *
         * It returns a Promise that resolves once all progress steps have been displayed,
         * along with the timeout ID to optionally allow cancelling the progress animation externally.
         *
         * @function
         * @returns {{promise: Promise<void>, timeoutId: number}}
         *   An object containing:
         *   - `promise`: Resolves when the last step is complete.
         *   - `timeoutId`: The ID of the last setTimeout, useful for canceling if needed.
         */
        function showFakeProgress() {
            const steps = [
                "Sending your letter information…",
                "Creating your letter…",
                "Applying the template…",
                "Adding your text…",
                "Adding your attachments…",
                "Finalizing…",
            ];

            let currentStep = 0;
            const progressBar = document.getElementById("progressBar");
            const progressText = document.getElementById("progressText");

            let timeoutId;

            const promise = new Promise((resolve) => {
                // TODO currently the progress is "fake", this logic needs to be refactored
                // in a real progress bar that makes sense.
                function updateProgress() {
                    if (currentStep < steps.length) {
                        const progress = ((currentStep + 1) / steps.length) * 100;
                        progressBar.style.width = `${progress}%`;
                        progressText.textContent = steps[currentStep];
                        currentStep++;
                        timeoutId = setTimeout(updateProgress, 1000);
                    } else {
                        resolve();
                    }
                }

                updateProgress();
            });

            return { promise, timeoutId };
        }

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
        function submitLetterRPC(data) {
            return rpc.query({
                route: "/my2/children/letters/new",
                params: data,
            });
        }

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
        async function handleResponse(mode, result, childId) {
            if (mode === "send") {
                window.location.href = `/my2/children/letters/${childId}?new_letter_generator_id=${result.generator_id}`;
            } else if (mode === "preview") {
                document.getElementById("previewImage").src = result.preview_url;
                $("#previewModal").modal("show");
            }
        }
    });
});
