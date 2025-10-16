document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.remove_attachment", function (require) {
        "use strict";

        const ToastService = require("my_compassion.toast_service");
        const rpc = require("web.rpc");
        const _t = require("web.core")._t;

        // Select all remove buttons
        const removeButtons = document.querySelectorAll(".remove-attachment-button");

        removeButtons.forEach((button) => {
            button.addEventListener("click", async function (event) {
                event.preventDefault();

                const attachmentId = button.getAttribute("data-id");
                if (!attachmentId) {
                    const msg = _t("Attachment ID is missing.");
                    ToastService.error(msg);
                    return;
                }

                try {
                    // Call Odoo route
                    const result = await rpc.query({
                        route: "/my2/letter/remove_attachment",
                        params: { attachment_id: parseInt(attachmentId, 10) },
                    });

                    // Check server response
                    if (result.success) {
                        const uploadedFile = button.closest(".uploaded-file");
                        if (uploadedFile) {
                            uploadedFile.remove();
                        } else {
                            console.warn("Unable to find the element to remove in the DOM.");
                        }
                    } else {
                        const msg = result.error || _t("Error occurred while removing the attachment.");
                        console.error("Server error:", msg, result);
                        ToastService.error(msg);
                    }
                } catch (error) {
                    console.error("JS error while removing attachment:", error);
                    ToastService.error(_t("Unable to remove the attachment."));
                }
            });
        });
    });
});
