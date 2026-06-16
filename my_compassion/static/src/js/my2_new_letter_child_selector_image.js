/** @odoo-module **/

/**
 * New-letter child selector: reloads the new-letter page for the chosen child
 * when the dropdown changes. The child's portrait is rendered server-side, so
 * this script only drives the navigation.
 *
 * Used in /templates/pages/my2_new_letter.xml
 */

import { whenReady } from "@odoo/owl";

whenReady(() => {
    const dropdown = document.getElementById("child-dropdown");
    if (!dropdown) {
        return;
    }

    // TODO: re-seed the form in place (rpc) on change instead of reloading the
    // whole new-letter page for each child.
    dropdown.addEventListener("change", (event) => {
        window.location.href = `/my2/children/letters/new?child_id=${event.target.value}`;
    });
});
