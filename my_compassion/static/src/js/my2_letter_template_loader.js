/**
 * Fetches a letter template from the server and populates the text input field with it.
 *
 * Used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener("DOMContentLoaded", () => {
    const textInput = document.getElementById("letter-input");
    const childSelector = document.getElementById("child-dropdown");
    const TEMPLATE_URL = `/my2/children/letter/templates`;

    const fetchTemplate = (childId) => {
        if (!textInput) {
            console.error("Required HTML element #letter-input is missing.");
            return;
        }
        fetch(`${TEMPLATE_URL}?child_id=${childId}`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                if (data && data.template_text) {
                    textInput.value = data.template_text;
                }
            })
            .catch((error) => {
                console.error("Failed to fetch template:", error);
            });
    };

    if (childSelector) {
        // Fetch template on initial load only if input is empty
        if (!textInput.value) {
            fetchTemplate(childSelector.value);
        }
        // Re-fetch template when child selection changes
        childSelector.addEventListener("change", (event) => {
            fetchTemplate(event.target.value);
        });
    }
});
