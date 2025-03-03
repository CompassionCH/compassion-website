/**
 * Dynamic Child Image Rendering in Vanilla JavaScript
 *
 * This script enables dynamic rendering of a child's image based on the selected option
 * from a dropdown. It uses plain JavaScript to update the DOM.
 *
 * Key Logic:
 * 1. A dropdown with the id `child-dropdown` allows users to select a child.
 * 2. When a child is selected, the `updateChildImage` function dynamically updates the
 *    image inside the container with id `child-reactive-img`.
 * 3. The selected child's ID is retrieved from the dropdown and used to generate the image URL.
 */

// Function to update the child image dynamically
function updateChildImage(childId) {
    const targetContainer = document.getElementById("child-reactive-img");

    // Clear the container before rendering a new image
    targetContainer.innerHTML = "";

    // Render the image only if a child is selected
    if (childId) {
        const img = document.createElement("img");
        img.className = "img-circle img-responsive ";
        img.src = `/web/image/compassion.child/${childId}/portrait`;
        img.alt = "Child image";

        targetContainer.appendChild(img);
    }
}

// Event handler for dropdown selection change
function onChildSelect(event) {
    const childId = event.target.value;
    updateChildImage(childId); // Update the child image with the selected ID
}

// Set up the dropdown change event listener and initialize the image
document.addEventListener("DOMContentLoaded", () => {
    const dropdown = document.getElementById("child-dropdown");
    const initialChildId = dropdown.value; // Get the initial selected child ID

    // Update the image on page load
    updateChildImage(initialChildId);

    // Add event listener to handle dropdown changes
    dropdown.addEventListener("change", onChildSelect);
});
