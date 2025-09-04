/**
 * Handles UI interactions for the my2_child_letter_card component:
 * - Highlights a newly created letter if indicated in URL.
 * - Updates envelope icon when view or download is triggered.
 *
 * Is used in /templates/pages/my2_child_letters.xml
 */
document.addEventListener("DOMContentLoaded", function () {

    window.onDownloadButtonClick = function (event) {
        handleIconOpen(event);
    };

    window.onLetterViewButtonClick = function (event) {
        handleIconOpen(event);
    };
});

/**
 * Updates the envelope icon within a clicked card to the "opened" state.
 */
function handleIconOpen(event) {
    // Find the parent card
    const card = event.currentTarget.closest(".details-card");
    if (!card) return;
    // Find the envelope icon in the card
    const icon = card.querySelector('i[name="iconLetter"]');
    if (icon) {
        icon.className = "fa letter-icon fa-envelope-open-o";
    }
}
