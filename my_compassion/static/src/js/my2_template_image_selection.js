/**
 * Handles the selection of template images by adding an ID to the clicked image
 * and removing it from any previously selected image.
 *
 * Is used in /templates/pages/my2_new_letter.xml
 */
document.addEventListener('DOMContentLoaded', function () {
    // Get all template images
    const templateImages = document.querySelectorAll('.template-image');

    // Add click event listener to each image
    templateImages.forEach(image => {
        image.addEventListener('click', function () {

            // Remove the 'selected-template' id from any previously selected image
            const previouslySelected = document.getElementById('selected-template');

            if (previouslySelected) {
                previouslySelected.removeAttribute('id');
            }

            // Set the 'selected-template' id to the clicked image
            image.setAttribute('id', 'selected-template');

            // Get the selected template ID from the data attribute
            const selectedTemplateId = image.getAttribute('data-template-id');
            // Log the selected template ID (for debugging)
            console.log('Selected Template ID: ', selectedTemplateId);
        });
    });
});