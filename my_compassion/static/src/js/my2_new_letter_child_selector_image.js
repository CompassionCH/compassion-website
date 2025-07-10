/**
 * Dynamic Child Image Rendering in Odoo 14.0 with Owl
 *
 * This script enables dynamic rendering of a child's image based on the selected option
 * from a dropdown.
 * The component is basically the child image and is re-rendered by owl when its state changes.
 *
 * Key Logic:
 * 1. A dropdown with the id child-dropdown allows users to select a child.
 * 2. When a child is selected, the `ChildSelectorImage` component updates its state
 *    and re-renders the image dynamically. The child image component is placed on the id child-reactive-img.
 * 3. Owl's `useState` is used to manage the selected child's ID, and the `mount` function
 *    is used to initialize the component.
 *
 * Note: Owl's `mount` is asynchronous, so we use `async/await` to ensure the component
 * is fully mounted before interacting with it.
 */

// Import necessary components from Owl manually
const { Component, mount, useState } = owl;
const { xml } = owl.tags;

/**
 * ChildSelectorImage Component
 *
 * Displays the image of the selected child. The image URL is dynamically generated
 * using the child's ID.
 */
class ChildSelectorImage extends Component {
    // Owl template for rendering the component
    static template = xml`
        <div class="child-image-container w-50 w-md-25">
            <!-- Render the image only if a child is selected -->
            <t t-if="state.selectedChildId">
                <img
                    class="img-circle img-responsive"
                    t-att-src="'/web/image/compassion.child/' + state.selectedChildId + '/portrait'"
                    alt="Child image" />
            </t>
        </div>
    `;

    constructor() {
        super(...arguments);
        this.state = useState({
            selectedChildId: this.props.selectedChildId || null,
        });
    }

    /**
     * Updates the selected child ID in the state.
     * This triggers a re-render of the component to display the new image.
     *
     * @param {number} childId - The ID of the selected child.
     */
    setSelectedChildId(childId) {
        this.state.selectedChildId = childId;
    }
}

// This will store the mounted component instance
let mountedComponent = null;

/**
 * Handles the dropdown selection change event.
 *
 * Retrieves the selected child's ID and updates the `ChildSelectorImage` component.
 *
 * @param {Event} event - The dropdown change event.
 */
function onChildSelect(event) {
    const childId = event.target.value;

    if (mountedComponent) {
        mountedComponent.setSelectedChildId(childId); // Call the method on the component instance
    }
}

/**
 * Mounts the `ChildSelectorImage` component and sets up the dropdown event listener.
 *
 * This function is asynchronous because Owl's `mount` function returns a Promise.
 */
async function mountImage() {
    const dropdown = document.getElementById("child-dropdown");
    dropdown.addEventListener("change", onChildSelect);

    const target = document.getElementById("child-reactive-img"); // Target container where we place the image
    if (target) {
        // Get the initial selected child ID from the dropdown
        const initialChildId = dropdown.value;

        // Mount the component and store the instance for later use
        mountedComponent = await mount(ChildSelectorImage, {
            target,
            props: { selectedChildId: initialChildId },
        });
    }
}

// Mount the component when the page is fully loaded
document.addEventListener("DOMContentLoaded", async () => {
    await mountImage();
});
