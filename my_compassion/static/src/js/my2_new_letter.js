/**
 * Handles the new_letter form submission.
 * Is used in /templates/pages/my2_new_letter.xml
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
            const templateId = document.getElementById("selected-template").getAttribute('data-template-id');
            const letterBody = document.getElementById("letter-input").value;

            const data = {
                child_id: childId,
                template_id: templateId,
                letter_body: letterBody,
                source: "mycompassion",
                csrf_token: odoo.csrf_token,
                attachments: null // TO DO
            };

            try {
                const result = await rpc.query({
                    route: "/my2/children/letter/new",
                    params: data
                });
                // Redirect the user to the child's letters page
                window.location.href = `/my2/children/${childId}/letters?new_letter_generator_id=${result.generator_id}`;
                // TO DO handle the success, the user needs a feedback confirmation on the letters page
            } catch (error) {
                // TO DO handle the error notification to the client
                console.error("Failed to create letter: ", error)
            }
        }
    });
});