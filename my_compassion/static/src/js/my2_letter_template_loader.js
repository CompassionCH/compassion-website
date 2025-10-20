/**
 * Fetches a letter template from the server and populates the text input field with it.
 *
 * Used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener("DOMContentLoaded", () => {
    const textInput = document.getElementById("letter-input");
    const childSelector = document.getElementById("child-dropdown");
    const selectedChildId = childSelector.value;

    if (textInput && !textInput.value) {
        fetch(`/my2/children/letter/templates?child_id=${selectedChildId}`)
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
    } else {
        console.error("Required HTML element #letter-input is missing.");
    }
});
