/**
 * Handles the selection of template images by adding an ID to the clicked image
 * and removing it from any previously selected image.
 *
 * Is used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener("DOMContentLoaded", function () {
    // Open the modal when the select element is clicked
    document.getElementById("template-selection").addEventListener("click", function (event) {
        event.preventDefault();
        $("#templateSelectionModal").modal("show");
    });

    // Get all template images
    const templateImages = document.querySelectorAll(".template-image");

    // Add click event listener to each image
    templateImages.forEach((image) => {
        image.addEventListener("click", function () {
            // Get the selected template ID from the data attribute
            const selectedTemplateId = image.getAttribute("data-template-id");
            const selectedTemplateName = image.getAttribute("data-template-name");
            const selectedTemplateImageLink = image.getAttribute("src");

            // Replace the button's label content with the template name selected
            const button_label_element = document.getElementById("template-selection-label");
            button_label_element.textContent = selectedTemplateName;

            // Add or replace the template image
            const targetDiv = document.getElementById("template-reactive-img");

            // CLear the div before rendering the template image
            targetDiv.innerHTML = "";

            // Render the template image
            const img = document.createElement("img");
            img.className = "img-fluid border shadow-sm";
            img.src = selectedTemplateImageLink;
            img.id = "selected-template";
            img.setAttribute("data-template-id", selectedTemplateId);

            targetDiv.appendChild(img);
        });
    });
});
