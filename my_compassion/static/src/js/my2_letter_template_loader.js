document.addEventListener("DOMContentLoaded", () => {
    textInput = document.getElementById("letter-input");

    // see if there is an active template for letter
    if (textInput) {
        fetch(`/my2/children/letter/templates`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                const template_text = data.template_text;
                textInput.value = template_text;
            })

            .catch((error) => {
                console.error("Failed to fetch template:", error);
            });
    } else {
        console.error("Required HTML element #letter-input is missing.");
    }
});
