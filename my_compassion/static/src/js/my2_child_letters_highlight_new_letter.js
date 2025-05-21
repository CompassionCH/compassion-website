/**
 * Highlights the newly created letter, when the user is redirected after creating a letter.
 *
 * It selects the element with the `data-generator-id` attribute and applies the
 * "new-letter-created" class when a matching ID is found in the URL.
 *
 * Is used in /templates/pages/my2_child_letters.xml
 */
document.addEventListener("DOMContentLoaded", function () {
  const urlParams = new URLSearchParams(window.location.search);
  const newLetterGeneratorId = urlParams.get("new_letter_generator_id");

  if (newLetterGeneratorId) {
    const newLetterElement = document.querySelector("[data-generator-id]");
    newLetterElement.classList.add("new-letter-created");
  }

  window.onDownloadButtonClick = function (event) {
    ReadIcon(event);
  };

  window.onLetterViewButtonClick = function (event) {
    ReadIcon(event);
  };

  function ReadIcon(event) {
    // Find the parent card
    const card = event.currentTarget.closest(".details-card");
    if (!card) return;
    // Find the envelope icon in the card
    const icon = card.querySelector('i[name="iconLetter"]');
    if (icon) {
      icon.className = "fa letter-icon fa-envelope-open-o";
    }
  }
});
