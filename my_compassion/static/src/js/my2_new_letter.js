/**
 * Handles the new_letter form submission.
 * Is used in /templates/pages/my2_new_letter.xml
 *
 * TODO: Compress the image, and ensure it is a JPEG
 * // [T2038] the new image name is necessary because the backend uses the
 * // extension as a hint to detect the mimetype.
 */
document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion", function (require) {
        "use strict";

        const rpc = require('web.rpc');

        // To trigger onSubmitLetter() when the form is submitted.
        const form = document.querySelector("form");
        if (form) {
            form.addEventListener("submit", onSubmitLetter);
        }

        /**
         * Captures the form data and sends it to the backend via an RPC call.
         * @param {Event} event - The form submission event.
         */
        async function onSubmitLetter(event) {

            // ensures that the form is handled via JavaScript,
            // allowing us to send the data via an RPC call instead of making a page reload.
            event.preventDefault();

            const selectedTemplateImage = document.getElementById("selected-template");
            const templateId = selectedTemplateImage ? selectedTemplateImage.getAttribute('data-template-id') : null;

            if (!selectedTemplateImage) {
                // TODO handle missing template logic in a friendly UI/UX way
                alert("Please select a template.");
                return;
            }

            const childId = document.getElementById("child-dropdown").value;
            const letterBody = document.getElementById("letter-input").value;

            const fileInput = document.getElementById("letter-attachments");
            const files = fileInput.files;
            let attachments = [];

            // Convert each file to a base64 string using promises
            const filePromises = Array.from(files).map(file => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.readAsDataURL(file);
                    reader.onload = function() {
                        resolve({
                            filename: file.name,
                            content: reader.result.split(',')[1] // Get the base64 content
                        });
                    };
                    reader.onerror = function() {
                        reject("Error reading file.");
                    };
                });
            });

            // Wait for all files to be processed
            try {
                attachments = await Promise.all(filePromises);
            } catch (error) {
                console.error("Failed to process files: ", error);
            }

            const submitButton = event.submitter;
            const mode = submitButton.getAttribute("data-mode") // define the send mode, either 'send' or 'preview'

            const data = {
                child_id: childId,
                template_id: templateId,
                letter_body: letterBody,
                source: "mycompassion",
                csrf_token: odoo.csrf_token,
                attachments: attachments,
                // attachments: JSON.stringify(attachments),
                mode: mode
            };

            console.log(data);

            try {
                const result = await rpc.query({
                    route: "/my2/children/letter/new",
                    params: data
                });

                if (result && mode === 'send') {
                    // Redirect the user to the child's letters page
                    window.location.href = `/my2/children/${childId}/letters?new_letter_generator_id=${result.generator_id}`;
                }

                if (result && mode === 'preview') {
                    document.getElementById("previewImage").src = result["preview_url"];
                        $("#previewModal").modal("show"); // Show the modal
                }
                // TO DO handle the success, the user needs a feedback confirmation on the letters page
            } catch (error) {
                // TO DO handle the error notification to the client
                console.error("Failed to create letter: ", error)
            }
        }
    });
});