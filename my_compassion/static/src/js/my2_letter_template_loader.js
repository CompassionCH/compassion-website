/**
 * Handles the selection of template images by adding an ID to the clicked image
 * and removing it from any previously selected image.
 *
 * Is used in /templates/pages/my2_new_letter.xml
 * Fetches a letter template from the server and populates the text input field with it.
 *
 * Used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener("DOMContentLoaded", () => {
    // Open the modal when the select element is clicked
    document.getElementById("letter_template").addEventListener("click", function (event) {
        event.preventDefault();
        $("#textTemplateSelectionModal").modal("show");
    });
    document.body.addEventListener("click", function (event) {
        const clickedButton = event.target.closest(".text-template-item");

        if (clickedButton) {
            const templateId = clickedButton.dataset.templateId;
            if (!templateId) {
                console.error("'data-template-id' is undefined.");
                return;
            }
            // Store the template ID in a hidden input for later use if needed
            const hiddenInput = document.getElementById("selected_template_id");
            if (hiddenInput) {
                hiddenInput.value = templateId;
            } else {
                console.error("Could not find '#selected_template_id' to store template ID.");
            }

            const childSelector = document.getElementById("child-dropdown");
            if (!childSelector) {
                console.error("Could not find '#child-dropdown'.");
                return;
            }
            const childId = childSelector.value;

            const TEMPLATE_URL = `/my2/children/letter/templates`;

            fetch(`${TEMPLATE_URL}?child_id=${childId}&template_id=${templateId}`)
                .then((response) => {
                    // 1. Open curly brace
                    if (!response.ok) {
                        throw new Error("Network response was not ok");
                    }
                    return response.json(); // 2. Explicit return
                }) // 3. Close curly brace
                .then((data) => {
                    if (data && data.template_text) {
                        const targetInput = document.getElementById("letter-input");
                        if (targetInput) {
                            targetInput.value = data.template_text;
                            // Trigger input event so framework/listeners detect the change
                            targetInput.dispatchEvent(new Event("input", { bubbles: true, cancelable: true }));
                        } else {
                            console.error("Could not find '#letter-input' for insertion.");
                        }
                    } else {
                        console.error("Fetch did not return 'template_text'.");
                    }
                })
                .catch((error) => {
                    console.error("Fetch failed:", error); // Fixed typo "etch"
                });
        }
    });
});
