/**
 * Handles the new_letter form submission.
 */
document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion", function (require) {
        "use strict";

        const rpc = require('web.rpc');

        // To trigger onSubmitLetter() when the form is submitted.
        const form = document.querySelector("form");
        if (form) {
            form.addEventListener("submit", onSubmitLetter);
        }

        /**
         * Captures the form data and sends it to the backend via an RPC call.
         * @param {Event} event - The form submission event.
         */
        async function onSubmitLetter(event) {

            // ensures that the form is handled via JavaScript,
            // allowing us to send the data via an RPC call instead of making a page reload.
            event.preventDefault();

            const childId = document.getElementById("child-dropdown").value;
            const templateId = document.getElementById("template-dropdown").value;
            const letterContent = document.getElementById("letter-input").value;

            const data = {
                child_id: childId,
                template_id: templateId,
                letter_content: letterContent
            };

            try {
                const result = await rpc.query({
                    route: "/my2/children/letter/new",
                    params: data
                });
            } catch (error) {
                console.error("Failed to create letter: ", error)
            }
        }
    });
});