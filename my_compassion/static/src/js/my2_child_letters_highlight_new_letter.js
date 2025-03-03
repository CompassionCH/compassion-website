/**
 * Highlights the newly created letter, when the user is redirected after creating a letter.
 *
 * It selects the element with the `data-generator-id` attribute and applies the
 * "new-letter-created" class when a matching ID is found in the URL.
 *
 * Is used in /templates/pages/my2_child_letters.xml
 */
document.addEventListener('DOMContentLoaded', function () {

    const urlParams = new URLSearchParams(window.location.search);
    const newLetterGeneratorId = urlParams.get("new_letter_generator_id");

    if (newLetterGeneratorId) {
        const newLetterElement = document.querySelector('[data-generator-id]')
        newLetterElement.classList.add("new-letter-created");
    }

});